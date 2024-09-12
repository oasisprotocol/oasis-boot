DESCRIPTION = "Minimal image that includes the Oasis stage 1 init."

PACKAGE_INSTALL = "stage1-init ${VIRTUAL-RUNTIME_base-utils} ${ROOTFS_BOOTSTRAP_INSTALL}"

INITRAMFS_MAXSIZE = "20000000"

IMAGE_FEATURES = ""

export IMAGE_BASENAME = "oasis-vm-stage1"
IMAGE_NAME_SUFFIX ?= ""
IMAGE_LINGUAS = ""

LICENSE = "MIT"

IMAGE_FSTYPES = "${INITRAMFS_FSTYPES}"

inherit core-image

IMAGE_ROOTFS_SIZE = "8192"
IMAGE_ROOTFS_EXTRA_SPACE = "0"

# Use the same restriction as initramfs-live-install
COMPATIBLE_HOST = "x86_64.*-linux"

# Make sure stage 1 rootfs contains /dev/console since we are embedding it into
# the kernel and thus replacing the default minimal initramfs which would otherwise
# provide the console device.
IMAGE_PREPROCESS_COMMAND:append = " stage1_prepare_rootfs"
stage1_prepare_rootfs() {
    mkdir ${IMAGE_ROOTFS}/dev
    mknod -m 622 ${IMAGE_ROOTFS}/dev/console c 5 1
}
