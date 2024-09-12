DESCRIPTION = "Minimal root filesystem for a stage2."

PACKAGE_INSTALL = "stage2-base busybox libgcc ${VIRTUAL-RUNTIME_base-utils} ${ROOTFS_BOOTSTRAP_INSTALL}"

IMAGE_FEATURES = ""

export IMAGE_BASENAME = "oasis-vm-stage2-basic"
IMAGE_NAME_SUFFIX ?= ""
IMAGE_LINGUAS = ""

LICENSE = "MIT"

IMAGE_FSTYPES = "tar.bz2"

inherit core-image

IMAGE_ROOTFS_SIZE = "8192"
IMAGE_ROOTFS_EXTRA_SPACE = "0"
