SUMMARY = "Pinned QEMU table builders for the Oasis TDX launch profile"
HOMEPAGE = "https://www.qemu.org/"
LICENSE = "GPL-2.0-or-later & LGPL-2.1-or-later"
LIC_FILES_CHKSUM = "file://COPYING;md5=a3b50d8b88dcc0eb3d7d39b760b9e821"

# This private native tool never replaces the distribution's QEMU. Its qtest
# accelerator initializes device models but never executes guest instructions.
SRC_URI = "https://download.qemu.org/qemu-${PV}.tar.xz \
           file://0002-configure-allow-recipe-managed-python.patch"
SRC_URI[sha256sum] = "e0517349b50ca73ebec2fa85b06050d5c463ca65c738833bd8fc1f15f180be51"
S = "${WORKDIR}/qemu-${PV}"
B = "${WORKDIR}/build"

inherit pkgconfig python3native native
DEPENDS = "glib-2.0-native zlib-native ninja-native"

# QEMU 10.1 requires Meson >=1.5.0, newer than Scarthgap's meson-native.
# Extract its source-archive-pinned wheels with the Python standard library;
# neither pip, a virtualenv, nor configure-time network access is needed.
export PYTHONPATH = "${B}/python-packages"
export OASIS_MESON = "${B}/oasis-meson"
do_configure[cleandirs] = "${B}"
do_configure[dirs] = "${B}"
do_compile[dirs] = "${B}"
do_install[dirs] = "${B}"

do_configure() {
    install -d ${B}/python-packages
    ${PYTHON} -m zipfile -e ${S}/python/wheels/meson-1.8.1-py3-none-any.whl ${B}/python-packages
    ${PYTHON} -m zipfile -e ${S}/python/wheels/pycotap-1.3.1-py3-none-any.whl ${B}/python-packages
    cat > ${OASIS_MESON} <<EOF
#!/bin/sh
exec ${PYTHON} -m mesonbuild.mesonmain "\$@"
EOF
    chmod 0755 ${OASIS_MESON}

    ${S}/configure --prefix=${prefix} --python=${PYTHON} \
        --cc="${CC}" --cxx="${CXX}" --host-cc="${BUILD_CC}" \
        --extra-cflags="${CFLAGS}" --extra-ldflags="${LDFLAGS}" \
        --ninja=${STAGING_BINDIR_NATIVE}/ninja \
        --with-pkgversion=oasis-tdx-qemu-v10.1 \
        --target-list=x86_64-softmmu --without-default-features \
        --enable-tcg --enable-kvm --disable-tools --disable-user \
        --disable-guest-agent --disable-docs --disable-download --disable-werror
}

do_compile() {
    ninja ${PARALLEL_MAKE} qemu-system-x86_64
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 qemu-system-x86_64 ${D}${bindir}/oasis-tdx-qemu
}
