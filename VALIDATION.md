# Validation — 2026-09-15

## Passed

- Repository checks: twelve specs, valid source manifests/full Git pins, no
  unresolved rpmautospec macros; Python and shell syntax checks.
- Eleven specs parse with RPM 4.20.1 using the Fedora 44/aarch64 target macros.
  The logos spec intentionally refuses preparation without its reviewed license.
- Seven SRPMs were generated with the shared builder and are in `dist/`:
  kernel, uboot-tools, m1n1, gravity-release, gravity-remix-scripts,
  gravity-platform-metapackage and gravity-appstream-metadata.
- Every generated SRPM has an accompanying SHA256 input manifest.
- The pinned kernel source SRPM checksum matches. Its Fedora/Asahi patch applies
  to Linux 7.1.13, followed by the generated Gravity M4 diff. Both pass
  `git apply --check` and apply without conflict.
- The kernel overlay adds CONFIG_DRM_ASAHI_M4=m to both 16K Fedora configs.
- All 53 patches in the U-Boot package apply in order. This includes the four
  missing Asahi NVMe prerequisite commits and the four Gravity commits.
- The patched Apple NVMe driver and Apple board source match the committed
  Gravity fork. Shared NVMe code also retains Fedora's DMA-mapping changes.
- The resulting packaged U-Boot source cross-builds successfully with
  `apple_m1_defconfig` and `aarch64-linux-gnu-gcc`, producing
  `u-boot-nodtb.bin`. That binary contains
  `gravity,efi-system-partition` and `apple,t8132-nvme-ans2`, and contains
  no `asahi,efi-system-partition` string.
- m1n1's source snapshot and Fedora Rust dependency patch prepare successfully.
  The Asahi artwork submodule is explicitly omitted in favor of gravity-logos.
- Two independently generated first-boot source archives have identical hashes.
- The current Gravity scripts working tree passes a staged Fedora install with
  the RPM's /usr/sbin and /etc/sysconfig paths. The Fedora dangling-DTB-symlink
  patch applies. This tested an isolated copy, not a published source revision.
- AppStream XML is well-formed; the COPR Makefile resolves the requested spec
  path to the expected package.

## Still pending

These checks used the Debian host's extracted RPM tooling and existing cross
compiler. SRPM generation is not a native Fedora binary-package build.

- Native Fedora 44/aarch64 mock or COPR binary builds and RPM linting.
- Kernel config regeneration/toolchain checks and kernel compilation.
- Mesa fork source/version selection and build.
- Publish/pin the scripts and installer changes, then build those RPMs.
- Artwork licensing, logos binary package and m1n1 binary package.
- COPR project/public-key configuration and gravity-repos build.
- Full dependency resolution and installation in the Fedora KDE image.
- appstreamcli semantic validation (the binary package's %check runs it).
- Hardware boot, firmware consumption, first-boot and package-update tests.

No builds have been uploaded to COPR, no release assets have been published,
and no hardware support is claimed from SRPM generation alone.
