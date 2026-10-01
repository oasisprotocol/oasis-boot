DESCRIPTION = "An implementation of docker-compose with podman backend"
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://LICENSE;md5=b234ee4d69f5fce4486a80fdaf4a4263"

inherit python_poetry_core

PV = "1.6.0+git"
SRC_URI = "\
    git://github.com/containers/podman-compose.git;branch=main;protocol=https \
    file://0001-Fix-issue-with-parsing-the-license-field.patch \
"

SRCREV = "0f6537e9cfa38f6035ac57c1716b6d55dbaf3ca4"

S = "${WORKDIR}/git"

DEPENDS += "python3-pyyaml-native"

RDEPENDS:${PN} += "\
    python3-asyncio \
    python3-dotenv \
    python3-json \
    python3-pyyaml \
    python3-unixadmin \
"
