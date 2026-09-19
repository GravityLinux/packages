# Validation — 2026-09-15

## 2026-09-18 Fedora config comparison fix (507.gravity)

- Config overlays now emit canonical disabled-option comments, not `=n`.
- Apple 16K overlays explicitly reconcile REGMAP_SPMI=m, QCOM_SCM=m and
  SND_COMPRESS_OFFLOAD=y with the selected drivers' Kconfig requirements.
- Overlay regression tests pass, including repeated application, disabled-option
  spelling, dependency values and preservation of non-16K variants.
- Ran tools/check_kernel_kconfig.py against pinned Linux 3cd0faa9ba07 and the
  existing extracted baseline SRPM SOURCES in .work/kernel-hobv6jv7/SOURCES.
  All eight Fedora AArch64 variants passed listnewconfig, olddefconfig and
  the baseline process_configs.sh AWK mismatch comparator, with no new options,
  config warnings or mismatches. Inputs were not modified.
- This tests Kconfig generation/comparison with Fedora's dummy GCC toolchain;
  it is not a complete RPM %prep, kernel compilation or hardware test.

## 2026-09-18 Apple 16K trim (506.gravity)

- Rebased the removable no-sleep policy onto published packages/main.
- Source pins match fetched Gravity kernel 3cd0faa9ba07, Mesa 353cfbc3154,
  bootloader 47d97ba32aef, installer 34c9ded9e2e4, and U-Boot a2f6913694f.
- Normal and debug 16K configurations pass listnewconfig (no new options)
  and olddefconfig using the pinned kernel and Fedora's dummy GCC toolchain.
- Normal module selections drop from 5596 to 4711; debug from 5600 to 4715.
  These are Kconfig selections, not measured binary size/build-time savings.
- Checked that Apple display/GPU/audio/NVMe/radio, USB storage/UAS/audio,
  virtio, filesystem and PM settings match their respective untrimmed configs.
  Normal retains both Asahi GPU drivers. The debug baseline already loses Rust
  with dummy GCC because KASAN requires Clang for Rust; the trim does not change
  that existing toolchain-dependent behavior.
- Overlay regression tests verify 16K-only scope and idempotence. No full
  kernel compilation or hardware test has been performed for this trim.

## 2026-09-18 J773g radio calibration

- Installer tests pass both with the bundled ASN.1 decoder and on the Fedora
  test image using Fedora's ASN.1 2.7.0 module (22 tests in each environment).
- The installer extracts BTBF and WCAL from local factory BWCl records, saves
  address-bound ESP filenames and raw-archive metadata, and reproduces them
  during firmware updates. No Apple calibration data is committed.
- U-Boot's checked-in Apple configuration now includes the 32 memory banks
  used in the working M4 test builds and 128 KiB of DT fixup padding.
- The updated U-Boot cross-build passes. A fresh m1n1 → U-Boot → EFI boot into
  the Fedora test image produces both calibration DT properties with exact
  matches to the local factory extraction (Bluetooth 15,040 bytes; Wi-Fi
  5,888 bytes). The Wi-Fi driver reports loading its platform calibration.
- Bluetooth initializes automatically with the already-pinned BCM4388
  beamforming-only probe fix compiled against the image's matching kernel
  development package. This is a test module, not a completed RPM rebuild.
  Bluetooth discovers nearby devices and Wi-Fi finds 25 access points.
  Association, pairing and throughput were not tested in this validation.
- A host libfdt harness exercises the actual U-Boot loader function, covering
  both address byte orders, existing-property preservation, missing/invalid/
  short files, invalid addresses and insufficient DT capacity.
- All 58 U-Boot RPM patches apply to the checksum-verified upstream tarball.
  The resulting Apple board source and defconfig match the committed fork
  byte for byte, and the patched package source cross-builds successfully.
  That exact package-derived U-Boot build also boots the Fedora test image
  through EFI with both matching calibration properties and working radios.
- Package input checks pass. New COPR binary builds remain required.

## 2026-09-16 downstream audio preparation

- Added a thirteenth recipe, rust-speakersafetyd, adapted from Fedora f44.
  Repository checks pass. Its missing source pin correctly blocks SRPM builds.
- The audio metapackage now requires the gravity-speakersafetyd capability
  supplied by our downstream daemon recipe; stock Fedora alone cannot satisfy it.
- The downstream fork was unavailable for inspection. Version, dependency
  licenses, Fedora patch reconciliation, model profiles and related UCM/audio
  policy packages remain unverified. This is a scaffold, not a completed build.
- Native RPM spec parsing was not rerun: the previously extracted temporary
  RPM tools are no longer available in this session. COPR builds and hardware
  safety validation remain pending.

## Passed

- Repository checks: twelve specs, valid source manifests/full Git pins, no
  unresolved rpmautospec macros; Python and shell syntax checks.
- Twelve specs parse with RPM 4.20.1; target-package checks use the Fedora
  44/aarch64 macros, and the logos package is noarch.
- Eleven packages have SRPMs generated with the shared builder in `dist/`:
  kernel, uboot-tools, m1n1, gravity-release, gravity-remix-scripts,
  gravity-platform-metapackage, gravity-appstream-metadata, gravity-scripts
  gravity-installer, gravity-logos and gravity-repos.
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

## COPR validation

- After the package rename, gravity-bootloader and gravity-scripts SRPMs build locally.
  The bootloader spec resolves to gravity-bootloader, gravity-bootloader-stage1 and
  gravity-bootloader-tools while retaining upstream m1n1 binary/configuration paths.
  A COPR binary build of the renamed package remains pending.

- User-submitted build [10989758](https://copr.fedorainfracloud.org/coprs/adevwithanidea/gravity/build/10989758/)
  succeeded for gravity-logos 20260915-101.gravity.fc44 in fedora-44-aarch64.
  rpmlint reported zero errors and eight warnings (including intentional
  duplicated notices for embedding consumers, virtual provides, and missing
  documentation/check sections).
- Retrieved the project's public key over HTTPS from the URL in COPR's repo
  file: https://download.copr.fedorainfracloud.org/results/adevwithanidea/gravity/pubkey.gpg
  Fingerprint: `6CBEBC85D891B94EEF48EA6115974442C8793EE4`.
  UID: `adevwithanidea_gravity (None) <adevwithanidea#gravity@copr.fedorahosted.org>`.
- Verified the COPR-built logos RPM's RSA/SHA256 signatures and digests with
  that key using a temporary isolated RPM database. This checks consistency
  with COPR's HTTPS-published key, not independent out-of-band identity proof.
- gravity-repos SRPM builds with the configured project URL and pinned key.

## Remaining release checks

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
- Logos installation tests and bootloader binary builds (renamed from m1n1).
- gravity-repos COPR binary build and installation tests.
- Full dependency resolution and installation in the Fedora KDE image.
- appstreamcli semantic validation (the binary package's %check runs it).
- Hardware boot, firmware consumption, first-boot and package-update tests.

The user uploaded the logos build to COPR; other package builds and release
publication remain pending. No hardware support is claimed from builds alone.
