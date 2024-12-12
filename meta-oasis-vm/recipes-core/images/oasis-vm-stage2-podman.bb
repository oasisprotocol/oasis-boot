DESCRIPTION = "Stage2 with Podman container support."

require common.inc

OASIS_PODMAN_INSTALL = "stage2-podman"

PACKAGE_INSTALL = "${OASIS_BASIC_INSTALL} ${OASIS_PODMAN_INSTALL} ${VIRTUAL-RUNTIME_base-utils} ${ROOTFS_BOOTSTRAP_INSTALL}"

export IMAGE_BASENAME = "oasis-vm-stage2-podman"
