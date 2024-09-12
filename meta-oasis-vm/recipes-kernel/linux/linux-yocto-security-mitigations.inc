FILESEXTRAPATHS:prepend := "${THISDIR}/linux-yocto:"

SRC_URI += "\
    ${@bb.utils.contains('MACHINE_FEATURES', 'security-mitigations', \
                         'file://security-mitigations.scc file://security-mitigations.cfg', '', d)} \
"
