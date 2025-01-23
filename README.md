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

The resulting artifacts will be located in `build/artifacts`.

## Targets

### `oasis-vm-stage1`

Builds the Stage 1 image which is a Linux kernel with an initramfs that can
load Stage 2 from the first available volume (e.g. `/dev/vda`). It expects the
volume to be linearly partitioned as follows:


* `part-rootfs` (start: `0` end: `storage_offset`) is the partition containing
  the root filesystem.

* `part-storage` (start: `storage_offset` end: `storage_offset + storage_size`)
  is the storage partition.

Where `storage_offset` and `storage_size` are obtained from the kernel command
line using the following parameters:

* `oasis.stage2.storage_offset` is the `storage_offset` in 512-byte sectors.
* `oasis.stage2.storage_size` is the `storage_size` in 512-byte sectors.

The partitions are set up by using dm-linear to map the regions into respective
block devices. In case the `storage_offset` is not defined, only `part-rootfs`
is mapped.

The root partition is expected to be a dm-verity device where its configuration
is also passed via the kernel command line. The following command line arguments
are expected:

* `oasis.stage2.roothash=ROOTHASH` where `ROOTHASH` should be the hex-encoded
  root hash of the dm-verity device.

* `oasis.stage2.hash_offset=OFFSET` where `OFFSET` should be a decimal number
  specifying the dm-verity hash offset within the Stage 2 image.

If the command line arguments are not provided, Stage 1 will panic. Otherwise
it will map `/dev/mapper/part-rootfs` using dm-verity and will then proceed to
mount the Stage 2 filesystem (which is expected to be squashfs). Finally, it
will switch the root filesystem to Stage 2 and execute `/init`.

### `oasis-vm-stage2-basic`

Builds the basic Stage 2 _template_ which is a squash filesystem containing a
minimal root filesystem that can be used as Stage 2 for a trivial Oasis runtime.

See below for information on using these templates.

### `oasis-vm-stage2-podman`

Builds the basic Stage 2 _template_ which is a squash filesystem containing a
minimal root filesystem that can be used as Stage 2 for a Podman container
based system.

See below for information on using these templates.

### `ovmf`

Builds the virtual firmware that performs early boot of a TD.

## Using Templates

These templates are meant to be used with the [Oasis CLI] using the `rofl build`
subcommand to build ROFL app images.

[Oasis CLI]: https://github.com/oasisprotocol/cli
