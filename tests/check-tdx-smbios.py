#!/usr/bin/env python3
"""Compare the release filter with upstream edk2 C, without booting a VM."""
import argparse
import importlib.util
import pathlib
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
with tempfile.TemporaryDirectory(prefix="oasis-smbios-test-") as tmp:
    directory = pathlib.Path(tmp)
    executable = directory / "oracle"
    subprocess.run(["cc", "-DMDEPKG_NDEBUG", "-D_PCD_GET_MODE_32_PcdTcgPfpMeasurementRevision=0",
                    "-fshort-wchar", "-ffunction-sections", "-fdata-sections", "-I"+str(edk2),
                    "-I"+str(edk2 / "MdePkg/Include"), "-I"+str(edk2 / "MdePkg/Include/X64"),
                    "-I"+str(edk2 / "MdeModulePkg/Include"), "-I"+str(edk2 / "SecurityPkg/Include"),
                    str(root / "tests/smbios-filter-oracle.c"), "-Wl,--gc-sections", "-o", str(executable)], check=True)
    executable.chmod(0o700)
    for hypervisor, qemu in [("qemu/v10.1", args.qemu_10_1), ("qemu/v8.2", args.qemu_8_2)]:
        for memory in (16, 2048, 2049, 2815, 2816, 2817, 16383, 16384, 16385, 32766, 32767, 32768, 32769, 1048576):
            for cpus in (1, 16, 255):
                q = profile.Qtest(qemu, hypervisor, memory, cpus, directory)
                try:
                    raw = profile.installed_smbios(q.files()["etc/smbios/smbios-tables"])
                finally:
                    q.close()
                expected = subprocess.check_output([str(executable)], input=raw)
                if expected != profile.filter_smbios(raw):
                    raise AssertionError((hypervisor, memory, cpus))
print("84 configurations match the upstream edk2 SMBIOS filter")
