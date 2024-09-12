SUMMARY = "Oasis VM Stage 1 init"
DESCRIPTION = "Init system that just launches stage 2"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"

PR = "r2"

RDEPENDS:${PN} = "busybox cryptsetup"

SRC_URI = "file://init \
          "

S = "${WORKDIR}"

do_configure() {
        :
}

do_compile() {
        :
}

do_install() {
        install -m 0755 ${WORKDIR}/init ${D}
}

FILES:${PN} = "/init"
RCONFLICTS:${PN} = "systemd"
