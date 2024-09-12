# Oasis VM

This repository contains the build system for the Oasis VM distribution, a
minimal Linux distribution to be used when provisioning Intel TDX virtual
machines.

## Building

In order to ensure a reproducible build you can use the prepared Makefile. It
uses a Docker container to perform the build in a controlled environment, so
make sure Docker is available.

```
make
```

The resulting images will be located in `build/tmp/deploy/images/tdx`.

## Targets

### `oasis-vm-stage1`

Builds the Stage 1 image which is a Linux kernel with an initramfs that can
load Stage 2 from the first available volume (e.g. `/dev/vda`). It expects the
volume to be a dm-verity device where the configuration must be passed via the
kernel command line.

The following command line arguments are expected:

* `oasis.stage2.roothash=ROOTHASH` where `ROOTHASH` should be the hex-encoded
  root hash of the dm-verity device.

* `oasis.stage2.hash_offset=OFFSET` where `OFFSET` should be a decimal number
  specifying the dm-verity hash offset within the Stage 2 image.

If the command line arguments are not provided, Stage 1 will panic. Otherwise
it will map `/dev/vda` using dm-verity and will then proceed to mount the
Stage 2 filesystem. Finally, it will switch the root filesystem to Stage 2 and
execute `/init`.

### `oasis-vm-stage2-basic`

Build the basic Stage 2 _template_ which is a `tar.bz2` archive containing a
minimal root filesystem that can be used as Stage 2 for a trivial Oasis runtime.

See below for information on using these templates.

## Using Templates

In order to prepare a proper Stage 2 image from the given template one should do
the following:

1. Unpack the template into a temporary directory, e.g. `workdir`.
1. Copy the built Oasis runtime binary into `workdir/init`.
1. Create a suitable filesystem from this directory, for example:
   ```
   dd if=/dev/zero of=${img} seek=${size} count=0 bs=1024
   mkfs.ext4 -E root_owner=0:0 ${img} -d workdir
   ```

   Note the `${size}` which defines the size of the filesystem and also the
   offset for the dm-verity hash tree.

1. Create a dm-verity compatible image:
   ```
   veritysetup format --data-block-size=4096 --hash-block-size=4096 ${img} ${img}.hash
   ```

   Record the root hash.

1. Concatenate the two files to obtain the final image:
   ```
   cat ${img} ${img}.hash > ${img}.img
   ```

You can then use the given image as Stage 2.
