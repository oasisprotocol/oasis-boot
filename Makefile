# Use Bash shell.
# NOTE: You can control which Bash version is used by setting the PATH
# appropriately.
SHELL := bash

# Docker command to use.
DOCKER ?= docker

# The build container image to use for building everything else.
BUILD_IMAGE := crops/poky@sha256:fe6976cc917b6e1d6d11583ef628a16a165c91e76715608e4a2ce4c84336617e

# Intermediate build artifacts dir.
INTERMEDIATE_ARTIFACTS_DIR := build/tmp/deploy/images/tdx
# Final build artifacts dir.
FINAL_ARTIFACTS_DIR := build/artifacts

# Default target.
all: build-outer

# Prepare Git submodules.
prepare:
	@git submodule update --init --recursive

# Target that should be run outside the container.
build-outer: prepare
	@$(DOCKER) run --rm -it \
		-v $(shell pwd):/workdir \
		-w /workdir \
		$(BUILD_IMAGE) \
		make build-inner

# Target that should be run inside the container to build everything.
build-inner:
	@source poky/oe-init-build-env build/ && \
		bitbake oasis-vm-stage1 && \
		bitbake oasis-vm-stage2-basic && \
		bitbake oasis-vm-stage2-podman && \
		bitbake ovmf
	@rm -rf $(FINAL_ARTIFACTS_DIR)
	@mkdir -p $(FINAL_ARTIFACTS_DIR)
	@cp $(INTERMEDIATE_ARTIFACTS_DIR)/ovmf.tdx.fd $(FINAL_ARTIFACTS_DIR)
	@cp $(INTERMEDIATE_ARTIFACTS_DIR)/oasis-vm-stage2-basic-tdx.tar.bz2 $(FINAL_ARTIFACTS_DIR)/stage2-basic.tar.bz2
	@cp $(INTERMEDIATE_ARTIFACTS_DIR)/oasis-vm-stage2-podman-tdx.tar.bz2 $(FINAL_ARTIFACTS_DIR)/stage2-podman.tar.bz2
	@cp $(INTERMEDIATE_ARTIFACTS_DIR)/bzImage-initramfs-tdx.bin $(FINAL_ARTIFACTS_DIR)/stage1.bin

# Cleanup.
clean:
	@rm -rf build/tmp

# Enter build environment.
shell:
	@$(DOCKER) run --rm -it \
		-v $(shell pwd):/workdir \
		-w /workdir \
		$(BUILD_IMAGE) \
		bash

# List of targets that are not actual files.
.PHONY: \
	all \
	build-outer \
	build-inner \
	clean \
	shell
