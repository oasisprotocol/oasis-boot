# Use Bash shell.
# NOTE: You can control which Bash version is used by setting the PATH
# appropriately.
SHELL := bash

# Docker command to use.
DOCKER ?= docker

# The build container image to use for building everything else.
BUILD_IMAGE := crops/poky@sha256:fe6976cc917b6e1d6d11583ef628a16a165c91e76715608e4a2ce4c84336617e

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
		bitbake oasis-vm-stage2-basic

# Cleanup.
clean:
	@rm -rf build/tmp

# List of targets that are not actual files.
.PHONY: \
	all \
	build-outer \
	build-inner \
	clean
