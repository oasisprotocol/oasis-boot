OASIS_BASIC_INSTALL = "stage2-base busybox libgcc libssl ca-certificates"

IMAGE_FEATURES = ""
IMAGE_NAME_SUFFIX ?= ""
IMAGE_LINGUAS = ""

LICENSE = "MIT"

IMAGE_FSTYPES = "tar.bz2"

inherit core-image

IMAGE_ROOTFS_SIZE = "8192"
IMAGE_ROOTFS_EXTRA_SPACE = "0"
