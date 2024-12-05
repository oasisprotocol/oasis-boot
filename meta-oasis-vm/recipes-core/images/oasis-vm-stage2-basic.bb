DESCRIPTION = "Minimal root filesystem for a stage2."

require common.inc

PACKAGE_INSTALL = "${OASIS_BASIC_INSTALL} ${VIRTUAL-RUNTIME_base-utils} ${ROOTFS_BOOTSTRAP_INSTALL}"

export IMAGE_BASENAME = "oasis-vm-stage2-basic"
