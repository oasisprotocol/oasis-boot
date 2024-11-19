SUMMARY = "Oasis VM Stage 2 base"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"

SRC_URI = "file://init.post-registration \
          "

RDEPENDS:${PN} = "busybox busybox-udhcpc"

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
        install -d ${D}/tmp
        install -d ${D}/etc/oasis
        install -m 0755 ${WORKDIR}/init.post-registration ${D}/etc/oasis/init.post-registration
        # Create a symlink to tmpfs as root is read-only.
        ln -s /tmp/resolv.conf ${D}${sysconfdir}/resolv.conf
}

FILES:${PN} = "/proc /sys /dev /lib64 /tmp /etc/oasis/init.post-registration ${sysconfdir}/resolv.conf"
