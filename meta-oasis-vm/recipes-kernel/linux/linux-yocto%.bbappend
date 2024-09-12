KMACHINE:tdx ?= "common-pc-64"
COMPATIBLE_MACHINE:tdx = "tdx"

KERNEL_FEATURES:append:tdx=" features/scsi/disk.scc"
KERNEL_FEATURES:append:tdx=" cfg/virtio.scc cfg/paravirt_kvm.scc cfg/fs/ext4.scc"
KERNEL_FEATURES:append:tdx=" tdx.scc tpm2.scc security-mitigations.scc disk-encryption.scc"

require ${@bb.utils.contains('DISTRO_FEATURES', 'oasisvm', 'linux-yocto-oasisvm.inc', '', d)}
