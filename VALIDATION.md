# Validation — 2026-09-15

## Passed

- Repository checks: twelve specs, valid source manifests/full Git pins, no
  unresolved rpmautospec macros; Python and shell syntax checks.
- Twelve specs parse with RPM 4.20.1; target-package checks use the Fedora
  44/aarch64 macros, and the logos package is noarch.
- Ten packages have SRPMs generated with the shared builder in `dist/`:
  kernel, uboot-tools, m1n1, gravity-release, gravity-remix-scripts,
  gravity-platform-metapackage, gravity-appstream-metadata, gravity-scripts
  gravity-installer and gravity-logos.
- CC-BY-4.0 is allowed-content and allowed-documentation in Fedora's license
  data. Artwork uses that license; its Python generator uses MIT, and the
  existing font license is unchanged. Trademark policy is separate.
- gravity-logos 20260915-101.gravity.fc44 builds as a noarch binary RPM with
  the local extracted RPM tooling. Its License tag is CC-BY-4.0, and its file
  list includes license, attribution and trademark notices plus all five assets.
  The host reports its missing RPM database; this is not native Fedora validation.
- Updated installer SRPM generation and all five firmware tests pass. The final
  m1n1 SRPM carrying the artwork notice dependency is in `dist/artwork-cc-by/`;
  the earlier same-version SRPM in `dist/` predates that final dependency change.
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
- The pinned Gravity scripts source archive passes a staged Fedora install with
  the RPM's /usr/sbin and /etc/sysconfig paths. The Fedora dangling-DTB-symlink
  patch applies. Its transactional firmware-update test and both Gravity-only
  ESP/dracut identity tests pass from the archive.
- The pinned installer source archive passes all five firmware/import tests;
  the renamed source-tree Python symlink resolves without either submodule.
  The installer boot-logo helper produces the expected m1n1 payload format.
- AppStream XML is well-formed; the COPR Makefile resolves the requested spec
  path to the expected package.

## Still pending

These checks used the Debian host's extracted RPM tooling and existing cross
compiler. SRPM generation is not a native Fedora binary-package build.

- Native Fedora 44/aarch64 mock or COPR binary builds and RPM linting.
- Kernel config regeneration/toolchain checks and kernel compilation.
- Mesa fork source/version selection and build.
- Publish the pinned scripts and installer commits, then build their binary
  RPMs. The optional standalone wheel smoke test could not run on this host
  because its Python has no pip module.
- Publish the installer's pinned Gravity artwork and bootloader submodule
  commits; build and test the full macOS installer bundle.
- Native Fedora validation of the logos package and m1n1 binary builds.
- COPR project/public-key configuration and gravity-repos build.
- Full dependency resolution and installation in the Fedora KDE image.
- appstreamcli semantic validation (the binary package's %check runs it).
- Hardware boot, firmware consumption, first-boot and package-update tests.

No builds have been uploaded to COPR, no release assets have been published,
and no hardware support is claimed from SRPM generation alone.
