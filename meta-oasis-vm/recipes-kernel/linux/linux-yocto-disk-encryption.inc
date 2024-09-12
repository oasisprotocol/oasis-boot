FILESEXTRAPATHS:prepend := "${THISDIR}/linux-yocto:"

SRC_URI += "\
    ${@bb.utils.contains('MACHINE_FEATURES', 'disk-encryption', \
                         'file://disk-encryption.scc file://disk-encryption.cfg', '', d)} \
"
