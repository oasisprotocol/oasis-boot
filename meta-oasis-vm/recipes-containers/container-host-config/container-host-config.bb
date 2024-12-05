HOMEPAGE = "https://git.yoctoproject.org/meta-virtualization"
SUMMARY =  "Configuration Package for container hosts"
DESCRIPTION = "Common / centralized configuration files for container hosts"

LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"

SRC_URI = " \
    file://containers.conf \
    file://storage.conf \
    file://registries.conf \
    file://policy.json \
"

do_install() {
    install -d ${D}${sysconfdir}/containers
    install -m 0644 ${WORKDIR}/containers.conf ${D}${sysconfdir}/containers/containers.conf
    install -m 0644 ${WORKDIR}/storage.conf ${D}${sysconfdir}/containers/storage.conf
    install -m 0644 ${WORKDIR}/registries.conf ${D}${sysconfdir}/containers/registries.conf
    install -m 0644 ${WORKDIR}/policy.json ${D}${sysconfdir}/containers/policy.json
}

BBCLASSEXTEND = "native nativesdk"
