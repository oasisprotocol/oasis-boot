FILESEXTRAPATHS:prepend := "${THISDIR}/linux-yocto:"

SRC_URI += "\
    ${@bb.utils.contains('MACHINE_FEATURES', 'tpm2', \
                         'file://tpm2.scc file://tpm2.cfg', '', d)} \
"
