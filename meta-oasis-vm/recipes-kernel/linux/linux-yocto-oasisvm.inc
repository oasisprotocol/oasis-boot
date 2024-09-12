FILESEXTRAPATHS:prepend := "${THISDIR}/linux-yocto:"

SRC_URI += "\
    ${@bb.utils.contains('DISTRO_FEATURES', 'oasisvm', \
                         'file://oasisvm.scc file://oasisvm.cfg', '', d)} \
"
