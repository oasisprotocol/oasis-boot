DESCRIPTION = "An implementation of docker-compose with podman backend"
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://LICENSE;md5=b234ee4d69f5fce4486a80fdaf4a4263"

inherit setuptools3

PV = "1.4.1+git"
SRC_URI = "git://github.com/containers/podman-compose.git;branch=1.4.x;protocol=https"

SRCREV = "b37076bc5e5a0f34d1f9e63cd3341ffda950fed8"

S = "${WORKDIR}/git"

DEPENDS += "python3-pyyaml-native"

RDEPENDS:${PN} += "\
    python3-asyncio \
    python3-dotenv \
    python3-json \
    python3-pyyaml \
    python3-unixadmin \
"
