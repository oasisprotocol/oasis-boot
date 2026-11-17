#!/usr/bin/env python3
"""Check direct-kernel bootorder against the Ubuntu TDX guest CCEL digest."""
import hashlib
import importlib.util
import pathlib
import unittest

root = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "tdx_profile", root / "meta-oasis-vm/recipes-core/ovmf/ovmf/tdx_profile.py")
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


class BootOrderTest(unittest.TestCase):
    def test_live_tdx_measurement(self):
        data = profile.direct_kernel_bootorder(
            b"/pci@i0cf8/scsi@3/disk@0,0\nHALT\0")
        # Captured from Ubuntu 2:8.2.2+ds-0ubuntu1.4+tdx1.1 with -kernel,
        # disk bootindex=1 and -boot menu=off,strict=on.
        self.assertEqual(hashlib.sha384(data).hexdigest(),
                         "45329364f8553f7a865a89b060d45b93fb530d7d3aee4c539f"
                         "bfc6f40df0a6e5c68168716f706fe4f26ff1f49905a97e")

    def test_reject_changed_exporter_layout(self):
        for data in (b"", b"/pci@i0cf8/scsi@3/disk@0,0\0",
                     b"/rom@genroms/linuxboot_dma.bin\n"
                     b"/pci@i0cf8/scsi@3/disk@0,0\nHALT\0"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                profile.direct_kernel_bootorder(data)


if __name__ == "__main__":
    unittest.main()
