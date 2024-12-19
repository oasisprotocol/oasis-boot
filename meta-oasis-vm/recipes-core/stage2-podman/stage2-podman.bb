SUMMARY = "Oasis VM Stage 2 with Podman"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"

SRC_URI = "file://80-podman \
          "

RDEPENDS:${PN} = " \
        stage2-base \
        podman \
        podman-compose \
        python3-unixadmin \
        python3-json \
        python3-logging \
"

S = "${WORKDIR}"

do_configure() {
        :
}

do_compile() {
        :
}

do_install() {
        install -d ${D}${sysconfdir}/oasis/post-registration.d
        install -m 0755 ${WORKDIR}/80-podman ${D}${sysconfdir}/oasis/post-registration.d/80-podman
}

FILES:${PN} = "${sysconfdir}/oasis/post-registration.d/80-podman"
