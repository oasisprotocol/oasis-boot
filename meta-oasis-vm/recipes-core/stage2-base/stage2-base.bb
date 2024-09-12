SUMMARY = "Oasis VM Stage 2 base"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"

S = "${WORKDIR}"

do_configure() {
        :
}

do_compile() {
        :
}

do_install() {
        ln -s lib ${D}/lib64
        install -d ${D}/proc
        install -d ${D}/sys
        install -d ${D}/dev
}

FILES:${PN} = "/proc /sys /dev /lib64"
