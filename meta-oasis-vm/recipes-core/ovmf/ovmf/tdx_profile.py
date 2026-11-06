#!/usr/bin/env python3
"""Export a finite QEMU launch model. qtest executes no guest instructions.

The application build uses the exported templates, not QEMU. All integers patched
into templates are explicitly enumerated below; the format contains no programs.
"""
import argparse
import base64
import gzip
import hashlib
import io
import json
import pathlib
import struct
import subprocess
import tempfile

FIRMWARE_PROTOCOL = "oasis-tdvf-v1"
# Hypervisor identifiers name complete, immutable launch contracts. v0/v1 are
# reserved for the legacy firmware stream, not aliases for these profiles.
PROFILES = {
    "qemu/v10.1": dict(machine="pc-q35-10.1", qemu_version="10.1.0",
                    source_sha256="e0517349b50ca73ebec2fa85b06050d5c463ca65c738833bd8fc1f15f180be51"),
    "qemu/v8.2": dict(machine="pc-q35-8.2", qemu_version="2:8.2.2+ds-0ubuntu1.4+tdx1.1",
                    source_sha256="5e692dd20950a819ff6550cd3974e00319a93f47c0a15f808c58df1a9e4d2478"),
}
MACHINE_OPTIONS = ",hpet=off,usb=off,vmport=off,smm=off,pic=off,pit=off,max-ram-below-4g=4G,smbios-entry-point-type=64"
PCI64_SIZE = 32 << 30
MAX_CPUS = 255
MAX_MEMORY = 1048576  # MiB, 1 TiB; below the SMBIOS extended-address thresholds.
FW_CFG_NAMES = ["etc/extra-pci-roots", "BootMenu", "etc/boot-menu-wait",
                "etc/reserved-memory-end", "opt/ovmf/X-PciMmio64Mb", "bootorder"]
SMBIOS_ARGS = ["type=0,vendor=Oasis,version=1,date=01/01/2026,uefi=on",
               "type=1,manufacturer=Oasis,product=ROFL,version=1",
               "type=3,manufacturer=Oasis,version=1",
               "type=4,sock_pfx=CPU,manufacturer=Oasis,version=1,processor-id=1",
               "type=17,manufacturer=Oasis,loc_pfx=DIMM,speed=0"]


def direct_kernel_bootorder(data):
    """Model the -kernel boot entry absent from the non-booting qtest export."""
    # Both pinned QEMUs' x86_load_linux register linuxboot_dma.bin at bootindex
    # 0 with fw_cfg DMA enabled. The ROFL disk has bootindex 1. Qtest omits
    # -kernel (and does not need kernel/option-ROM binaries), so add only the
    # corresponding fw_cfg entry; it does not affect ACPI or SMBIOS tables.
    if data != b"/pci@i0cf8/scsi@3/disk@0,0\nHALT\0":
        raise ValueError("unexpected qtest bootorder for direct kernel boot")
    return b"/rom@genroms/linuxboot_dma.bin\n" + data


def ram_layout(memory):
    # Q35's default low-memory cap is 4 GiB; its layout switches at 2816 MiB.
    return (memory << 20, 0) if memory < 2816 else (2048 << 20, (memory-2048) << 20)


def values(memory):
    low, high = ram_layout(memory)
    base = ((1 << 32)+high+PCI64_SIZE-1) & -PCI64_SIZE
    return dict(low_ram=low, pci32_size=0xe0000000-low,
                pci64_base=base, pci64_end=base+PCI64_SIZE-1,
                memory_kib=memory*1024, dimm_mib=min(memory, 32767), extended_dimm_mib=memory if memory >= 32767 else 0,
                last_dimm_mib=(memory-1) % 16384+1,
                low_end_kib=low//1024-1, high_end_kib=((1 << 32)+high)//1024-1)


def encode(data):
    return base64.b64encode(data).decode("ascii")


def template(data, patches):
    # Zero all variable fields, so a template cannot accidentally retain a sample.
    out = bytearray(data)
    for p in patches:
        out[p["offset"]:p["offset"]+p["width"]] = bytes(p["width"])
    return dict(data=encode(out), patches=patches)


def expand(tpl, memory):
    out = bytearray(base64.b64decode(tpl["data"], validate=True))
    v = values(memory)
    for p in tpl["patches"]:
        out[p["offset"]:p["offset"]+p["width"]] = v[p["value"]].to_bytes(p["width"], "little")
    return bytes(out)


def patch(offset, width, value):
    return dict(offset=offset, width=width, value=value)


def unique(data, needle):
    off = data.find(needle)
    if off < 0 or data.find(needle, off+1) >= 0:
        raise ValueError("QEMU table layout changed: resource descriptor is not unique")
    return off


def acpi_template(data, memory):
    v = values(memory)
    off32 = unique(data, struct.pack("<IIIII", 0, v["low_ram"], 0xdfffffff, 0, v["pci32_size"]))
    # Match whole address descriptors, including their AML type/flags. QEMU's
    # inclusive maximum and constant length must agree with the pinned window.
    off64 = unique(data, b"\x8a\x2b\x00\x00\x0c\x03" + struct.pack(
        "<QQQQQ", 0, v["pci64_base"], v["pci64_end"], 0, PCI64_SIZE))
    return template(data, [patch(off32+4, 4, "low_ram"), patch(off32+16, 4, "pci32_size"),
                           patch(off64+14, 8, "pci64_base"), patch(off64+22, 8, "pci64_end")])


def smbios_entries(data):
    off = 0
    while off < len(data):
        if len(data)-off < 6 or data[off+1] < 4:
            raise ValueError("malformed SMBIOS structure")
        end = data.find(b"\0\0", off+data[off+1])
        if end < 0:
            raise ValueError("unterminated SMBIOS strings")
        yield off, data[off], data[off+1], end+2
        off = end+2
    if off != len(data):
        raise ValueError("truncated SMBIOS table")


def installed_smbios(data):
    # SmbiosPlatformDxe installs all QEMU records except 127. SmbiosDxe appends
    # its own type 127 with GetMaxSmbiosHandle() == 0xfeff (SMBIOS >= 2.1).
    out = bytearray(data)
    entries = list(smbios_entries(data))
    if not entries or entries[0][1] != 0 or entries[-1][1] != 127:
        raise ValueError("profile requires an explicit QEMU type 0 and final type 127")
    off = entries[-1][0]
    out[off:] = b"\x7f\x04\xff\xfe\0\0"
    return bytes(out)


def filter_smbios(data):
    # The subset generated by this profile, from edk2 SmbiosMeasurementDxe.
    # String filtering preserves byte length by replacing contents with spaces.
    fields = {1: [(7, 1, True), (8, 16, False), (24, 1, False)],
              3: [(7, 1, True), (8, 1, True)],
              4: [(32, 1, True), (33, 1, True), (34, 1, True),
                  (35, 1, False), (36, 1, False), (37, 1, False),
                  (42, 2, False), (44, 2, False), (46, 2, False),
                  (17, 1, False), (22, 2, False)],
              17: [(24, 1, True), (25, 1, True), (26, 1, True)]}
    out = bytearray(data)
    for off, typ, length, end in smbios_entries(data):
        if typ not in (0, 1, 3, 4, 16, 17, 19, 32, 127):
            raise ValueError(f"unexpected SMBIOS type {typ}")
        for field, size, string in fields.get(typ, []):
            if field+size > length:
                continue
            if string and out[off+field]:
                idx = out[off+field]
                start = off+length
                for _ in range(idx-1):
                    start = data.index(b"\0", start, end)+1
                stop = data.index(b"\0", start, end)
                out[start:stop] = b" "*(stop-start)
            out[off+field:off+field+size] = bytes(size)
    return bytes(out)


def smbios_key(hypervisor, memory):
    key = "low" if memory < 2816 else "high"
    if hypervisor == "qemu/v8.2":
        key += "-" + str((memory+16383)//16384)
    return key


def smbios_template(data, hypervisor, memory):
    out = filter_smbios(installed_smbios(data))
    patches, dimms, ranges = [], [], []
    for off, typ, _, _ in smbios_entries(out):
        if typ == 16:
            patches.append(patch(off+7, 4, "memory_kib"))
        elif typ == 17:
            dimms.append(off)
        elif typ == 19:
            ranges.append(off)
    if not dimms or len(ranges) not in (1, 2):
        raise ValueError("unexpected SMBIOS memory map")
    count = (memory+16383)//16384 if hypervisor == "qemu/v8.2" else 1
    if len(dimms) != count:
        raise ValueError("unexpected SMBIOS DIMM count")
    if hypervisor == "qemu/v8.2":
        # Full 16 GiB records, handles and locator strings are static for this
        # device count. Only the last record's size depends on exact RAM size.
        patches.append(patch(dimms[-1]+12, 2, "last_dimm_mib"))
    else:
        patches.append(patch(dimms[0]+12, 2, "dimm_mib"))
        patches.append(patch(dimms[0]+28, 4, "extended_dimm_mib"))
    patches.append(patch(ranges[0]+8, 4, "low_end_kib"))
    if len(ranges) == 2:
        patches.append(patch(ranges[1]+8, 4, "high_end_kib"))
    return template(out, patches)


class Qtest:
    def __init__(self, qemu, hypervisor, memory, cpus, directory):
        # Sparse shared RAM reserves address space without committing guest RAM.
        ram = directory / "qtest-ram"
        with ram.open("wb") as f:
            f.truncate(memory << 20)
        # No TDX object, KVM, /dev/vhost-vsock or CPU execution is involved.
        # A second virtio-serial function reserves the vsock slot. Both expose
        # the same 16 KiB modern 64-bit BAR, no ROM or ACPI table callback.
        args = [qemu, "-accel", "qtest", "-machine", PROFILES[hypervisor]["machine"]+MACHINE_OPTIONS,
                "-cpu", "max,vendor=GenuineIntel,phys-bits=48", "-m", str(memory),
                "-object", f"memory-backend-file,id=ram,size={memory}M,mem-path={ram},share=on,prealloc=off",
                "-machine", "memory-backend=ram",
                "-smp", f"cpus={cpus},maxcpus={cpus},sockets=1,cores={cpus},threads=1",
                "-nodefaults", "-no-user-config", "-display", "none", "-serial", "null",
                "-monitor", "none", "-qtest", "stdio",
                "-qtest-log", "/dev/null", "-S", "-boot", "menu=off,strict=on",
                "-global", "q35-pcihost.pci-hole64-size=32G",
                "-fw_cfg", "name=opt/ovmf/X-PciMmio64Mb,string=32768",
                "-device", "virtio-serial-pci,id=serial0,bus=pcie.0,addr=0x1,max_ports=1",
                "-device", "virtio-serial-pci,id=vsock-slot,bus=pcie.0,addr=0x2,max_ports=1",
                "-blockdev", "driver=null-co,node-name=drive0,size=1048576",
                "-device", "virtio-blk-pci,drive=drive0,id=disk0,bus=pcie.0,addr=0x3,bootindex=1",
                "-netdev", "user,id=net0,restrict=on",
                "-device", "virtio-net-pci,netdev=net0,id=nic0,bus=pcie.0,addr=0x4,romfile="]
        # No backend is necessary to construct virtio-net's firmware tables.
        pos = args.index("-netdev")
        del args[pos:pos+2]
        args[-1] = args[-1].replace("netdev=net0,", "")
        for s in SMBIOS_ARGS:
            args += ["-smbios", s]
        bios = directory / "qtest-bios.bin"
        bios.write_bytes(bytes(65536))
        args += ["-bios", str(bios)]
        self.log = open(directory / "qemu.log", "w+")
        self.proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log)

        # PlatformMiscInitialization / PciExBarInitialization in the pinned
        # firmware run before AcpiPlatformDxe. Reproduce these chipset writes
        # directly; no firmware is executed. Then model the 64-bit BAR allocation
        # and EnablePciDecoding() state at AcpiPlatformDxe's first fw_cfg read.
        try:
            for address, value in [(0x80000060, 0), (0x80000064, 0),
                                   (0x80000060, 0xe0000001), (0x8000f840, 0x601),
                                   (0x8000f844, 0x80), (0x8000f804, 0x1),
                                   (0x8000f8f0, 0xfed1c001)]:
                self.command(f"outl 0xcf8 {address}")
                self.command(f"outl 0xcfc {value}")
            self.allocate_pci64(memory)
        except BaseException:
            self.close()
            raise

    def pci_read(self, slot, offset):
        self.command(f"outl 0xcf8 {0x80000000 | slot << 11 | offset}")
        return int(self.command("inl 0xcfc"), 0)

    def pci_write(self, slot, offset, value):
        self.command(f"outl 0xcf8 {0x80000000 | slot << 11 | offset}")
        self.command(f"outl 0xcfc {value}")

    def allocate_pci64(self, memory):
        # The four root-bus virtio functions have exactly one 64-bit BAR each.
        # PciBusDxe combines prefetchable/non-prefetchable resources and orders
        # equal-alignment nodes on insertion (and again when merging).
        # PciHostBridgeDxe allocates bottom-up. With no bridges/hotplug, four
        # 16 KiB BARs fit at the aperture base. Only their aggregate range enters
        # Q35 ACPI; the individual BAR order does not affect measured bytes.
        base = values(memory)["pci64_base"]
        for index, slot in enumerate((1, 2, 3, 4)):
            for offset in (0x10, 0x14, 0x18, 0x1c):
                if self.pci_read(slot, offset) & 7 == 4:
                    raise ValueError("unexpected additional 64-bit PCI BAR")
            if self.pci_read(slot, 0x20) != 0x0c or self.pci_read(slot, 0x24) != 0:
                raise ValueError("unexpected virtio modern BAR layout")
            self.pci_write(slot, 0x20, 0xffffffff)
            self.pci_write(slot, 0x24, 0xffffffff)
            mask = (self.pci_read(slot, 0x24) << 32) | (self.pci_read(slot, 0x20) & ~15)
            if ((~mask & ((1 << 64)-1))+1) != 0x4000:
                raise ValueError("virtio 64-bit BAR size changed")
            address = base + index*0x4000
            self.pci_write(slot, 0x20, (address & 0xffffffff) | 0x0c)
            self.pci_write(slot, 0x24, address >> 32)
            # Status is write-one-to-clear: write only the command bits.
            self.pci_write(slot, 0x04, (self.pci_read(slot, 0x04) & 0xffff) | 2)

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
        self.proc.wait(timeout=10)
        self.proc.stdin.close()
        self.proc.stdout.close()
        self.log.close()

    def command(self, cmd):
        self.proc.stdin.write(cmd.encode()+b"\n")
        self.proc.stdin.flush()
        response = self.proc.stdout.readline().decode().strip()
        if not response.startswith("OK"):
            self.log.flush()
            self.log.seek(0)
            raise RuntimeError(f"qtest: {cmd[:60]}: {response}: {self.log.read()}")
        return response[2:].strip()

    def fwcfg(self, selector, size):
        # QEMU fw_cfg DMA reads avoid one round-trip per byte. Guest RAM is only
        # a buffer for the host test protocol; no vCPU executes instructions.
        descriptor = struct.pack(">IIQ", (selector << 16) | 0x08 | 0x02, size, 0x200000)
        self.command(f"write 0x100000 16 0x{descriptor.hex()}")
        self.command("outl 0x514 0")
        self.command("outl 0x518 0x1000")  # bswap32(0x100000)
        if self.command("read 0x100000 4") != "0x00000000":
            raise RuntimeError("fw_cfg DMA failed")
        return bytes.fromhex(self.command(f"read 0x200000 {size}")[2:])

    def files(self):
        count = struct.unpack(">I", self.fwcfg(0x19, 4))[0]
        directory = self.fwcfg(0x19, 4+count*64)
        result = {"BootMenu": self.fwcfg(0x0e, 2)}
        wanted = set(FW_CFG_NAMES + ["etc/acpi/tables", "etc/acpi/rsdp", "etc/table-loader", "etc/smbios/smbios-tables"])
        for off in range(4, len(directory), 64):
            size, selector, _, name = struct.unpack_from(">IHH56s", directory, off)
            name = name.rstrip(b"\0").decode()
            if name in wanted:
                result[name] = self.fwcfg(selector, size)
        result["bootorder"] = direct_kernel_bootorder(result["bootorder"])
        return result


def check_tdx_acpi(data, hypervisor):
    """Fail if the private Ubuntu tool omitted TDX's interrupt-table state."""
    if hypervisor != "qemu/v8.2":
        return
    start = unique(data, b"APIC")
    end = start + struct.unpack_from("<I", data, start+4)[0]
    if end > len(data):
        raise ValueError("truncated MADT")
    off, overrides = start+44, []
    while off < end:
        typ, size = data[off:off+2]
        if size < 2 or off+size > end:
            raise ValueError("malformed MADT entry")
        if typ == 2:
            overrides.append(struct.unpack_from("<BBIH", data, off+2))
        off += size
    expected = [(0, i, 2 if i == 0 else i, 5) for i in range(16)]
    if overrides != expected:
        raise ValueError("Ubuntu qtest tool did not reproduce TDX edge-triggered MADT")


def export_profile(qemu, hypervisor, max_cpus=MAX_CPUS):
    version = subprocess.check_output([qemu, "--version"], text=True).splitlines()[0]
    upstream = "8.2.2" if hypervisor == "qemu/v8.2" else "10.1.0"
    expected = f"QEMU emulator version {upstream} (oasis-tdx-{hypervisor.replace('/', '-')})"
    if version != expected:
        raise ValueError(f"profile requires the pinned private exporter: {expected}; got {version}")
    result = dict(PROFILES[hypervisor], acpi={}, smbios={}, fw_cfg=[])
    with tempfile.TemporaryDirectory(prefix="oasis-profile-") as tmp:
        directory = pathlib.Path(tmp)
        def snapshot(memory, cpus):
            q = Qtest(qemu, hypervisor, memory, cpus, directory)
            try:
                return q.files()
            finally:
                q.close()
        first = snapshot(1024, 1)
        result["fw_cfg"] = [dict(name=n, data=encode(first[n])) for n in FW_CFG_NAMES if n in first and first[n]]
        expected_cfg = [("BootMenu", b"\0\0"), ("opt/ovmf/X-PciMmio64Mb", b"32768"),
                        ("bootorder", b"/rom@genroms/linuxboot_dma.bin\n/pci@i0cf8/scsi@3/disk@0,0\nHALT\0")]
        if result["fw_cfg"] != [dict(name=n, data=encode(d)) for n, d in expected_cfg]:
            raise ValueError("unexpected measured fw_cfg entries")
        for cpus in range(1, max_cpus+1):
            sample = first if cpus == 1 else snapshot(1024, cpus)
            check_tdx_acpi(sample["etc/acpi/tables"], hypervisor)
            result["acpi"][str(cpus)] = dict(tables=acpi_template(sample["etc/acpi/tables"], 1024),
                rsdp=encode(sample["etc/acpi/rsdp"]), loader=encode(sample["etc/table-loader"]))
            if filter_smbios(installed_smbios(sample["etc/smbios/smbios-tables"])) != filter_smbios(installed_smbios(first["etc/smbios/smbios-tables"])):
                raise ValueError("SMBIOS unexpectedly depends on CPU count")
        # Below 2816 MiB RAM is all low; split configurations have two records.
        samples = [1024, 4096]
        if hypervisor == "qemu/v8.2":
            samples += [n*16384 for n in range(2, 65)]
        for memory in samples:
            sample = snapshot(memory, 1)
            key = smbios_key(hypervisor, memory)
            result["smbios"][key] = smbios_template(sample["etc/smbios/smbios-tables"], hypervisor, memory)
        # Verify both sides of memory-layout/size-encoding boundaries, the smallest
        # configuration, and the upper bound, directly against QEMU's builders.
        memories = {16, 17, 1023, 1025, 2047, 2048, 2049, 2815, 2816, 2817, 4095, 4096, 4097, 32766, 32767, 32768, MAX_MEMORY}
        # Above the RAM split, high-RAM end is (memory + 2048) MiB. Test both
        # sides of every 32 GiB aperture-placement boundary through 1 TiB.
        for n in range(1, 33):
            memories.update([n*32768-2049, n*32768-2048, n*32768-2047])
        for n in range(1, 65):
            memories.update([n*16384-1, n*16384])
            if n < 64:
                memories.add(n*16384+1)
        for memory in sorted(memories):
            cpus = 1 if memory % 2 else max_cpus
            sample = snapshot(memory, cpus)
            key = smbios_key(hypervisor, memory)
            a = result["acpi"][str(cpus)]
            expected = {"etc/acpi/tables": expand(a["tables"], memory),
                        "etc/acpi/rsdp": base64.b64decode(a["rsdp"]),
                        "etc/table-loader": base64.b64decode(a["loader"])}
            for name, data in expected.items():
                if sample[name] != data:
                    raise ValueError(f"{name} model mismatch: {memory} MiB, {cpus} CPUs")
            if expand(result["smbios"][key], memory) != filter_smbios(installed_smbios(sample["etc/smbios/smbios-tables"])):
                raise ValueError(f"SMBIOS model mismatch: {memory} MiB")
            actual_cfg = [dict(name=n, data=encode(sample[n])) for n in FW_CFG_NAMES if n in sample and sample[n]]
            if actual_cfg != result["fw_cfg"]:
                raise ValueError(f"fw_cfg unexpectedly varies: {memory} MiB")
    return result


def export(qemu_10_1, qemu_8_2, firmware, firmware_protocol):
    # The reviewed build recipe declares the protocol. It is bound to the
    # exact firmware bytes in the catalog, without modifying the firmware.
    if firmware_protocol != FIRMWARE_PROTOCOL:
        raise ValueError("unsupported firmware measurement protocol")
    fw = pathlib.Path(firmware).read_bytes()
    cfv_hash = "344bc51c980ba621aaa00da3ed7436f7d6e549197dfe699515dfa2c6583d95e6412af21c097d473155875ffd561d6790"
    if hashlib.sha384(fw[:0x84000]).hexdigest() != cfv_hash:
        raise ValueError("catalog requires pristine OVMF configuration volume")
    profiles = {}
    for hypervisor, qemu in [("qemu/v10.1", qemu_10_1), ("qemu/v8.2", qemu_8_2)]:
        profiles[hypervisor] = export_profile(qemu, hypervisor)
    return dict(version=2, firmware_protocol=firmware_protocol,
                firmware_sha256=hashlib.sha256(fw).hexdigest(),
                max_memory_mib=MAX_MEMORY, max_cpus=MAX_CPUS, profiles=profiles)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--qemu-10-1", required=True)
    p.add_argument("--qemu-8-2", required=True)
    p.add_argument("--firmware-protocol", required=True, choices=[FIRMWARE_PROTOCOL])
    p.add_argument("--firmware", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    profile = export(args.qemu_10_1, args.qemu_8_2, args.firmware, args.firmware_protocol)
    data = (json.dumps(profile, sort_keys=True, separators=(",", ":"))+"\n").encode()
    compressed = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=compressed, mode="wb", mtime=0) as out:
        out.write(data)
    pathlib.Path(args.output).write_bytes(compressed.getvalue())


if __name__ == "__main__":
    main()
