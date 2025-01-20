SUMMARY = "Oasis VM Stage 2 base"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"

SRC_URI = "file://init.post-registration \
           file://00-network \
          "

RDEPENDS:${PN} = " \
        busybox \
        busybox-udhcpc \
        cryptsetup \
        e2fsprogs-mke2fs \
        e2fsprogs-resize2fs \
        e2fsprogs-e2fsck \
"

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
        install -d ${D}/run
        install -d ${D}/storage

        install -d ${D}${sysconfdir}/oasis
        install -d ${D}${sysconfdir}/oasis/post-registration.d
        install -m 0755 ${WORKDIR}/init.post-registration ${D}${sysconfdir}/oasis/init.post-registration
        install -m 0755 ${WORKDIR}/00-network ${D}${sysconfdir}/oasis/post-registration.d/00-network

        # Create a symlink to tmpfs as root is read-only.
        ln -s /tmp/resolv.conf ${D}${sysconfdir}/resolv.conf
}

FILES:${PN} = "/proc \
               /sys \
               /dev \
               /lib64 \
               /tmp \
               /run \
               /storage \
               ${sysconfdir}/oasis/post-registration.d/00-network \
               ${sysconfdir}/oasis/init.post-registration \
               ${sysconfdir}/resolv.conf"
