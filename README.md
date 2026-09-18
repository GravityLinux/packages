# Gravity Linux RPM packaging

Twelve source packages for the first Fedora 44 / aarch64 / KDE release.
Each directory contains one RPM spec and its packaging files. Application and
driver code remains in separate Git repositories; sources are pinned in
[sources.json](sources.json). Repository names do not have a Gravity prefix;
Gravity-specific RPMs do.

## Packages

| Source RPM | Main output / role | Packaging baseline |
| --- | --- | --- |
| kernel | kernel-16k, core, modules, modules-core, modules-extra, devel | Asahi 7.1.13-403 SRPM |
| mesa | Fedora Mesa libraries, DRI and Vulkan drivers | Fedora 44 dist-git |
| uboot-tools | uboot-tools, uboot-images-armv8 | Asahi packaging plus six Gravity patches |
| gravity-bootloader | gravity-bootloader, gravity-bootloader-stage1, gravity-bootloader-tools | Fedora 44 m1n1 packaging, pinned M4 fork |
| gravity-scripts | gravity-scripts, gravity-fwupdate, dracut-gravity, update-m1n1, linux-firmware-vendor, gravity-battery | Fedora packaging and Gravity consumers |
| gravity-installer | python3-gravity_firmware and gravity-fwextract | Linux half of installer packaging |
| gravity-platform-metapackage | core, audio, plasma, desktop, fex, mesa integration | Asahi platform dependencies plus Gravity packages |
| gravity-repos | Gravity repository configuration and signing key | Gravity |
| gravity-remix-scripts | ESP extra-RPM installation and first-boot swap | Asahi first-boot scripts |
| gravity-release | common, basic and KDE release identity/defaults | Asahi release packaging |
| gravity-appstream-metadata | OS identity for software centers | Gravity |
| gravity-logos | Bootloader and desktop logos | Gravity artwork |
| rust-speakersafetyd | speakersafetyd (provides gravity-speakersafetyd) | Downstream audio fork; source pin and validation pending |

U-Boot's AArch64 image build is limited to `apple_m1`; host utilities are retained.

The package/dependency set retains Asahi's KDE platform dependencies, including
older Apple hardware support. Ordinary Fedora packages such as alsa-ucm-asahi,
asahi-audio, tiny-dfr, GRUB, shim, linux-firmware, wireless-regdb,
muvm and FEX are consumed from Fedora unless we need downstream changes.
A dependency's presence does not establish M4 hardware support.

Speaker protection must use our downstream fork, not Fedora's stock daemon.
See [the speakersafetyd preparation checklist](rust-speakersafetyd/README.md).
Matching UCM and audio-policy forks may also be needed; their requirements
must be confirmed with the audio developer.

AVD firmware packaging is excluded from this release. Bluetooth is not a release
requirement. Extracted Apple firmware and IPSWs must never enter this repository,
an SRPM, or COPR. The installer creates the machine-specific firmware archive;
the Linux firmware-tool RPM only contains extraction code. The macOS installer
bundle and bootloader release assets are built separately.

## Current release inputs

Run `make status` for unresolved inputs:

- Publish the pinned scripts and installer source commits to their Gravity URLs.
- Mesa is temporarily pinned to Gravity's main at `4bd3d1801ae6` (26.3.0-devel)
  for hardware image testing. Confirm the final release revision with Niklas.
- Confirm and pin the speakersafetyd fork and reconcile its version, Cargo
  dependencies and safety profiles with the prepared rust-speakersafetyd spec.
- COPR is configured as `adevwithanidea/gravity`; its public signing key is
  pinned in `gravity-repos/RPM-GPG-KEY-gravity`.
- Publish the pinned artwork revision: artwork is CC BY 4.0, the generator is
  MIT, and the existing font license is preserved. Trademark policy is separate.
  Fedora's [license data](https://gitlab.com/fedora/legal/fedora-license-data/-/blob/main/data/CC-BY-4.0.toml)
  lists CC BY 4.0 as allowed for content and documentation, not generally code.
- Publish the pinned M4 source at GravityLinux/bootloader.

Empty refs and repository credentials are intentional unresolved inputs, not
working defaults. Nothing is submitted or published automatically.

## Build SRPMs

Use Fedora 44 for authoritative builds. Install these source-build tools there:

```sh
sudo dnf install python3 git make rpm-build redhat-rpm-config \
  systemd-rpm-macros python3-rpm-macros pyproject-rpm-macros \
  cargo-rpm-macros rust-srpm-macros cpio gzip xz mock copr-cli
make check
make status
```

First fetch and review previously unpinned HTTPS inputs:

```sh
make prepare PACKAGE=uboot-tools ARGS=--update-lock
git diff -- downloads.lock.json
```

Commit reviewed download hashes before COPR builds. Later preparations verify
the hashes. Existing local patches are pinned by the packaging Git revision;
Git source snapshots are pinned by full commit IDs. The kernel's base SRPM has
a separately pinned SHA256.

```sh
make srpm PACKAGE=uboot-tools
make srpm PACKAGE=gravity-remix-scripts
make srpm PACKAGE=kernel ARGS='--source-dir ../linux'
```

A clean local checkout can supply the pinned commit with `--source-dir`.
Uncommitted source changes are rejected. Packaging changes belong here; source
changes should be committed in the corresponding source repository first.
Every run gets an isolated `.work/` directory. SRPMs and their input hashes
are placed in `dist/`. Existing SRPM filenames are never overwritten: bump
Release or choose another `--outdir` for a test rebuild.

The kernel builder extracts the pinned Asahi SRPM's configs and auxiliary
sources, generates a diff from the matching Asahi source commit to Gravity's
commit, and adds that after the Fedora/Asahi patch stack. This preserves Fedora
kernel-specific changes. `kernel/gravity.config` enables the M4 GPU and built-in
J773g speaker support, including its dependencies, in both 16K Fedora
configurations. Keep the kernel SRPM, base_ref, ref, version and config changes
in sync on each kernel rebase; check the patch stack again.

For Mesa, keep Fedora's complete subpackage split and Rust dependency
packaging. Pinning a new source version may require adapting the Meson options,
vendored dependency versions and file lists. A source pin alone is not a build
test.

## COPR and build order

Use [Git-backed COPR builds](COPR.md) to build directly from GitHub without
uploading local SRPMs. It includes the exact form settings and webhook setup.

Create one project with the `fedora-44-aarch64` chroot. Configure that project
to make already built packages available to subsequent builds.

1. Independent: kernel, Mesa, uboot-tools, gravity-installer, gravity-logos,
   rust-speakersafetyd (once its source inputs are ready),
   gravity-release, gravity-appstream-metadata, gravity-remix-scripts.
2. gravity-bootloader after gravity-logos.
3. gravity-scripts after gravity-bootloader, uboot-images-armv8 and python3-gravity_firmware
   are available for installation tests.
4. gravity-repos after project/key configuration; gravity-platform-metapackage
   last, then test the complete image dependency transaction.

Building independent SRPMs does not require their runtime dependencies.
Building the image does.

For an explicit local SRPM upload:

```sh
copr-cli build OWNER/PROJECT dist/uboot-tools-2026.07-200.gravity.fc44.src.rpm
```

For SCM builds, point COPR at GravityLinux/packages, pin a packaging revision,
choose `make_srpm`, leave the subdirectory empty, and set Spec File to
`uboot-tools/uboot-tools.spec` (or another package's relative path).
[.copr/Makefile](.copr/Makefile) derives the package name from that spec path,
installs the source-build tools inside COPR's worker, and invokes the same
builder. See the [official COPR instructions](https://docs.copr.fedorainfracloud.org/user_documentation.html#scm).

The binary build can run without network access once all source inputs are
included in the SRPM. Keep COPR tokens in the user's COPR configuration, outside
Git. Snapshot final SRPMs/RPMs to Gravity release storage before shipping; COPR
retention is not a release archive.

## Image integration and validation

Install `gravity-platform-metapackage`, `gravity-release-kde`, and
`gravity-release-identity-kde` in the KDE image. The metapackage brings in
Gravity repositories, release identity, logos and first-boot scripts alongside
Asahi platform dependencies. Fedora's base/update repositories remain enabled.

The boot consumer uses:
- `/usr/lib64/m1n1/m1n1.bin`
- `/usr/share/uboot/apple_m1/u-boot-nodtb.bin`
- Apple DTBs from `/boot/dtb`
- the Gravity system ESP selected by the existing Gravity scripts

Keep Apple hardware identifiers, historical changelogs and upstream credits.
They are not distro fallback paths. Gravity extras use `/boot/efi/gravity/extras`.
The old Fedora Asahi branding repair and macOS-27 migration actions are omitted
for these new installs.

Before shipping, require successful native Fedora mock/COPR binary builds,
inspection of the RPM file lists/dependencies, a complete image dependency
transaction, and a hardware boot/update test. In particular, verify the 16K M4
kernel config, m1n1/DTB/U-Boot assembly, firmware handoff, and that the Gravity
repository wins over Fedora for the forked packages.

See [VALIDATION.md](VALIDATION.md) for what has actually been tested and
[UPSTREAM.md](UPSTREAM.md) for imported packaging provenance.
