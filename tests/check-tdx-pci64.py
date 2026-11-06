#!/usr/bin/env python3
"""Check the offline PCI window against pinned edk2 C and both QEMU builders.

The host oracle compiles upstream functions verbatim, with minimal host-service
stubs. It checks override handling, natural alignment, resource merging, and
bottom-up allocation independently of the exporter's Python arithmetic.
"""
import argparse
import importlib.util
import pathlib
import re
import struct
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--edk2", required=True)
p.add_argument("--qemu-10-1", required=True)
p.add_argument("--qemu-8-2", required=True)
args = p.parse_args()
root = pathlib.Path(__file__).resolve().parent.parent
edk2 = pathlib.Path(args.edk2).resolve()
spec = importlib.util.spec_from_file_location("tdx_profile", root / "meta-oasis-vm/recipes-core/ovmf/ovmf/tdx_profile.py")
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


def function(path, name):
    text = (edk2 / path).read_text()
    # Upstream functions have their closing brace at column zero. Retain the
    # full signature/body without edits; reject missing/ambiguous definitions.
    matches = re.findall(r"(?:^STATIC\n)?^(?:VOID|UINT64)\n(?:EFIAPI\n)?" + name + r" \(.*?^}\n", text, re.M | re.S)
    if len(matches) != 1:
        raise ValueError(f"expected exactly one upstream function: {name}")
    return matches[0]


memdetect = "OvmfPkg/Library/PlatformInitLib/MemDetect.c"
resources = "MdeModulePkg/Bus/Pci/PciBusDxe/PciResourceSupport.c"
functions = [(memdetect, n) for n in ("PlatformGetFirstNonAddressCB", "PlatformGetFirstNonAddress", "PlatformDynamicMmioWindow")]
functions += [(resources, n) for n in ("InsertResourceNode", "MergeResourceTree", "CalculateResourceAperture")]
functions += [("MdeModulePkg/Bus/Pci/PciHostBridgeDxe/PciHostBridge.c", "AllocateResource")]
memories = {16, 2048, 2049, 2815, 2816, 2817, 1048576}
for n in range(1, 33):
    memories.update([n*32768-2049, n*32768-2048, n*32768-2047])
with tempfile.TemporaryDirectory(prefix="oasis-pci64-test-") as tmp:
    directory = pathlib.Path(tmp)
    (directory / "pci64-upstream.inc").write_text("\n".join(function(path, name) for path, name in functions))
    oracle = directory / "oracle"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-I"+str(directory),
                    str(root / "tests/pci64-oracle.c"), "-o", str(oracle)], check=True)
    count = 0
    for memory in sorted(memories):
        # Address-width-dependent dynamic sizing must remain disabled.
        outputs = [subprocess.check_output([str(oracle), str(memory), str(bits)], text=True)
                   for bits in (46, 48, 52)]
        if len(set(outputs)) != 1:
            raise AssertionError("PCI window depends on host physical address width")
        base, end, *bars = map(int, outputs[0].split())
        v = profile.values(memory)
        assert (base, end) == (v["pci64_base"], v["pci64_end"])
        descriptor = b"\x8a\x2b\0\0\x0c\x03" + struct.pack("<QQQQQ", 0, base, end, 0, end-base+1)
        for hypervisor, qemu in (("qemu/v10.1", args.qemu_10_1), ("qemu/v8.2", args.qemu_8_2)):
            q = profile.Qtest(qemu, hypervisor, memory, 1, directory)
            try:
                actual = [(q.pci_read(slot, 0x24)<<32) | (q.pci_read(slot, 0x20)&~15) for slot in (1,2,3,4)]
                assert sorted(actual) == sorted(bars), (hypervisor, memory, actual, bars)
                assert q.files()["etc/acpi/tables"].count(descriptor) == 1, (hypervisor, memory)
            finally:
                q.close()
            count += 1
print(f"{count} QEMU windows match upstream edk2 C at three physical address widths")
