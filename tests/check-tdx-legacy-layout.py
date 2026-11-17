#!/usr/bin/env python3
"""Compare explicit PCI/CPU/RAM settings with Q35's legacy automatic layout.

Only these three settings are varied. The new firmware's other platform settings
remain pinned; this is not a claim that old firmware has the new RTMR0 stream.
"""
import argparse
import importlib.util
import pathlib
import re
import tempfile
from unittest import mock

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--qemu-10-1", required=True)
p.add_argument("--qemu-8-2", required=True)
args = p.parse_args()
root = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("tdx_profile", root / "meta-oasis-vm/recipes-core/ovmf/ovmf/tdx_profile.py")
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)
popen = profile.subprocess.Popen


def legacy_layout(command, **kwargs):
    command = [re.sub(r",bus=pcie\.0,addr=0x[1-4]", "", s).replace(
        ",max-ram-below-4g=4G", "") for s in command]
    pos = command.index("-smp") + 1
    command[pos] = command[pos].split(",")[0].removeprefix("cpus=")
    return popen(command, **kwargs)


with tempfile.TemporaryDirectory(prefix="oasis-layout-test-") as tmp:
    directory = pathlib.Path(tmp)
    count = 0
    for hypervisor, qemu in (("qemu/v10.1", args.qemu_10_1), ("qemu/v8.2", args.qemu_8_2)):
        for memory in (16, 2048, 2049, 2815, 2816, 30720, 30721, 1048576):
            for cpus in (1, 2, 16, 255):
                snapshots = []
                for factory in (popen, legacy_layout):
                    with mock.patch.object(profile.subprocess, "Popen", factory):
                        q = profile.Qtest(qemu, hypervisor, memory, cpus, directory)
                        try:
                            snapshots.append(q.files())
                        finally:
                            q.close()
                assert snapshots[0] == snapshots[1], (hypervisor, memory, cpus)
                count += 1
print(f"{count} explicit PCI/CPU/RAM layouts match Q35's legacy defaults")
