SUMMARY = "Ubuntu Noble TDX QEMU table builders for the Oasis launch catalog"
HOMEPAGE = "https://github.com/canonical/tdx"
LICENSE = "GPL-2.0-or-later & LGPL-2.1-or-later"
LIC_FILES_CHKSUM = "file://COPYING;md5=441c28d2cf86e15a37fa47e15a72fbac"

# Match 2:8.2.2+ds-0ubuntu1.4+tdx1.1, including ALL Ubuntu/TDX patches.
# The host's installed QEMU is not used: Ubuntu removes its qtest modules.
UBUNTU_QEMU_URI = "https://ppa.launchpadcontent.net/kobuk-team/tdx-release/ubuntu/pool/main/q/qemu"
SRC_URI = "${UBUNTU_QEMU_URI}/qemu_8.2.2+ds.orig.tar.xz;name=source \
           ${UBUNTU_QEMU_URI}/qemu_8.2.2+ds-0ubuntu1.4+tdx1.1.debian.tar.xz;name=packaging;subdir=qemu-8.2.2 \
           file://0001-qtest-tdx-acpi-state.patch \
           file://0002-configure-allow-recipe-managed-python.patch"
SRC_URI[source.sha256sum] = "5e692dd20950a819ff6550cd3974e00319a93f47c0a15f808c58df1a9e4d2478"
SRC_URI[packaging.sha256sum] = "e2bf4ee6f40d48ac683480f6b25cc9628f1f0cc45159b623653b698b97d309da"
S = "${WORKDIR}/qemu-8.2.2"
B = "${WORKDIR}/build"

inherit pkgconfig python3native native
DEPENDS = "glib-2.0-native zlib-native dtc-native ninja-native meson-native"

# Ubuntu's +ds archive omits the Meson wheel. QEMU 8.2 accepts meson-native
# 1.3.1 (minimum 0.63.0); use it directly without QEMU's venv/pip bootstrap.
# libfdt is required by this version's x86_64-softmmu target. The patch command
# used below is already supplied by Yocto HOSTTOOLS, not an extra native recipe.
export OASIS_MESON = "${STAGING_BINDIR_NATIVE}/meson"

# Apply the source package's ordered series before the exporter-only hook.
python apply_ubuntu_patch_series() {
    import pathlib
    import subprocess
    source = pathlib.Path(d.getVar('S'))
    stamp = source / '.oasis-ubuntu-patches-applied'
    if stamp.exists():
        return
    patches = source / 'debian/patches'
    for line in (patches / 'series').read_text().splitlines():
        name = line.strip()
        if not name or name.startswith('#'):
            continue
        subprocess.run(['patch', '--batch', '-p1', '-i', str(patches / name)],
                       cwd=source, check=True)
    stamp.touch()
}
do_patch[prefuncs] += "apply_ubuntu_patch_series"

do_configure[cleandirs] = "${B}"
do_configure[dirs] = "${B}"
do_compile[dirs] = "${B}"
do_install[dirs] = "${B}"
do_configure() {
    ${S}/configure --prefix=${prefix} --python=${PYTHON} \
        --cc="${CC}" --cxx="${CXX}" --host-cc="${BUILD_CC}" \
        --extra-cflags="${CFLAGS}" --extra-ldflags="${LDFLAGS}" \
        --ninja=${STAGING_BINDIR_NATIVE}/ninja \
        --with-pkgversion=oasis-tdx-qemu-v8.2 \
        --target-list=x86_64-softmmu --without-default-features \
        --disable-install-blobs \
        --enable-tcg --enable-kvm --disable-tools --disable-user \
        --disable-guest-agent --disable-docs --disable-download --disable-werror
}
do_compile() {
    ninja ${PARALLEL_MAKE} qemu-system-x86_64
}
do_install() {
    install -d ${D}${bindir}
    install -m 0755 qemu-system-x86_64 ${D}${bindir}/oasis-tdx-qemu-ubuntu
}
