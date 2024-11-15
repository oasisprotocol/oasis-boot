KBRANCH ?= "v6.10/standard/tiny/base"

LINUX_KERNEL_TYPE = "tiny"
KCONFIG_MODE = "--allnoconfig"

require recipes-kernel/linux/linux-yocto.inc

# CVE exclusions
include recipes-kernel/linux/cve-exclusion_6.10.inc

LINUX_VERSION ?= "6.10.3"
LIC_FILES_CHKSUM = "file://COPYING;md5=6bc538ed5bd9a7fc9398086aedcd7e46"

DEPENDS += "${@bb.utils.contains('ARCH', 'x86', 'elfutils-native', '', d)}"
DEPENDS += "openssl-native util-linux-native"

KMETA = "kernel-meta"
KCONF_BSP_AUDIT_LEVEL = "2"

SRCREV_machine ?= "92466d9d49ed65d9a13f2ab648a92becc027a257"
SRCREV_meta ?= "9e63c08171dc88ed8a5ed8ecc4b508465ea75352"

PV = "${LINUX_VERSION}+git"

SRC_URI = "git://git.yoctoproject.org/linux-yocto.git;branch=${KBRANCH};name=machine;protocol=https \
           git://git.yoctoproject.org/yocto-kernel-cache;type=kmeta;name=meta;branch=yocto-6.10;destsuffix=${KMETA};protocol=https \
           file://0001-tsm-Runtime-measurement-register-support.patch \
           file://0002-tsm-Add-RTMRs-to-the-configfs-tsm-hierarchy.patch \
           file://0003-tsm-Map-RTMRs-to-TCG-TPM-PCRs.patch \
           file://0004-tsm-Allow-for-extending-and-reading-configured-RTMRs.patch \
           file://0005-x86-tdx-Add-tdx_mcall_rtmr_extend-interface.patch \
           file://0006-virt-tdx-guest-Add-RTMR-based-measurement-update-sup.patch"

COMPATIBLE_MACHINE = "^(qemux86|qemux86-64|qemuarm64|qemuarm|qemuarmv5)$"

# Functionality flags
KERNEL_FEATURES = ""

KERNEL_DEVICETREE:qemuarmv5 = "arm/versatile-pb.dtb"
