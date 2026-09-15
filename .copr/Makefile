# COPR SCM: choose make_srpm and set Spec File to PACKAGE/PACKAGE.spec.
ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
PACKAGE ?= $(basename $(notdir $(spec)))
.PHONY: srpm
srpm:
	test -n "$(PACKAGE)"
	dnf -y install python3 git rpm-build redhat-rpm-config systemd-rpm-macros python3-rpm-macros pyproject-rpm-macros cargo-rpm-macros rust-srpm-macros cpio gzip xz
	python3 "$(ROOT)/tools/package.py" srpm "$(PACKAGE)" --outdir "$(outdir)"
