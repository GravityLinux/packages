# Gravity Linux RPM packaging

Seventeen source packages for the first Fedora 44 / aarch64 / KDE release.
Each directory contains one RPM spec and its packaging files. Application and
driver code remains in separate Git repositories; sources are pinned in
[sources.json](sources.json). Repository names do not have a Gravity prefix;
Gravity-specific RPMs do.

## Packages

| Source RPM | Main output / role | Packaging baseline |
| --- | --- | --- |
| kernel | kernel-16k, core, modules, modules-core, modules-extra, devel (provides kernel(p3s)): the one release kernel for every board (Linux 7.3 + P3S, M4) | Fedora 7.3.3-200.fc44 SRPM on Linux 7.3 |
| mesa | Fedora Mesa libraries, DRI and Vulkan drivers; gravity-flatpak-graphics hardware extensions for freedesktop 25.08/26.08 and Fedora f45 | Fedora 44 dist-git and Gravity SDK build |
| mesa-fex-guest | x86_64 and i686 builds of the same Mesa source, assembled into the two x86 trees below (built in the fedora-44-x86_64 chroot only) | Gravity |
| gravity-x86-mesa | gravity-x86-mesa and fex-guestos-mesa: the x86 trees of the pinned mesa-fex-guest build, repacked as noarch packages for gravity-x86's FEX root filesystem and Steam's FEX tool | Gravity |
| uboot-tools | uboot-tools, uboot-images-armv8 | Asahi packaging plus six Gravity patches |
| gravity-bootloader | gravity-bootloader, gravity-bootloader-stage1, gravity-bootloader-tools | Fedora 44 m1n1 packaging, pinned M4 fork |
| gravity-scripts | gravity-scripts, gravity-fwupdate, dracut-gravity, update-m1n1, linux-firmware-vendor, gravity-battery | Fedora packaging and Gravity consumers |
| gravity-installer | python3-gravity_firmware and gravity-fwextract | Linux half of installer packaging |
| gravity-platform-metapackage | core, audio, plasma, desktop, fex, mesa integration | Asahi platform dependencies plus Gravity packages |
| gravity-repos | Gravity repository configuration and signing key | Gravity |
| gravity-remix-scripts | ESP extra-RPM installation (swap: Fedora default zram, SWAP-POLICY.md); sleep allowed only where suspend-to-idle works (SLEEP-POLICY.md) | Asahi first-boot scripts |
| gravity-release | common, basic and KDE release identity/defaults | Asahi release packaging |
| gravity-appstream-metadata | OS identity for software centers | Gravity |
| gravity-logos | Bootloader and desktop logos | Gravity artwork |
| gravity-audio-j713 | J713 UCM profiles, DSP rules and speakersafetyd profile for Fedora's audio packages | Gravity |
| gravity-x86 | gravity-x86: FEX x86 programs with 4K pages on P3S kernels (rootfs service, binfmt rules) | Gravity |
| steam | steam and steam-gravity-proton-default: launcher for Valve's native ARM64 Steam client. Each user's first start downloads the client from Valve and the ARM64 Proton build from Gravity Linux; neither is packaged | Gravity |

U-Boot's AArch64 image build is limited to `apple_m1`; host utilities are retained.

The package/dependency set retains Asahi's KDE platform dependencies, including
older Apple hardware support. Ordinary Fedora packages such as
tiny-dfr, GRUB, shim, linux-firmware, wireless-regdb,
muvm and FEX are consumed from Fedora unless we need downstream changes.
A dependency's presence does not establish M4 hardware support.

Audio uses Fedora's alsa-ucm-asahi, asahi-audio and speakersafetyd unchanged.
gravity-audio-j713 adds the J713 (MacBook Air 13", M4) UCM profiles, the
WirePlumber rules that give it the J413 speaker and mic graphs, and its
speakersafetyd profile, in directories those packages already read; see
[gravity-audio-j713](gravity-audio-j713/README.md).

AVD firmware packaging is excluded from this release. Bluetooth is not a release
requirement. Extracted Apple firmware and IPSWs must never enter this repository,
an SRPM, or COPR. The installer creates the machine-specific firmware archive;
the Linux firmware-tool RPM only contains extraction code. The macOS installer
bundle and bootloader release assets are built separately.

## Current release inputs

Run `make status` for unresolved inputs:

- Publish the pinned scripts and installer source commits to their Gravity URLs.
- Mesa 26.3.0~devel-110.gravity pins `f66f380c6485`; publish that source
  before remote builds, and use `--source-dir` for local validation.
- The x86 Mesa repack needs a pin after mesa-fex-guest 110 is built; publish
  native Mesa and both repacked x86 packages together.
- Validate the J713 speakersafetyd profile on hardware (gravity-audio-j713/README.md).
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

The kernel builder extracts the pinned Fedora SRPM's configs and auxiliary
sources, generates a diff from upstream Linux (`base_ref`, the release the
kernel.org tarball holds) to Gravity's commit, and applies it after Fedora's
patch. This keeps Fedora's kernel-specific changes and configuration.
`kernel/gravity-aarch64.config` sets the options Gravity's source adds in every
AArch64 variant; `kernel/gravity.config` adds P3S and the Apple M4 drivers to
both 16K configurations (see kernel/TRIMMING.md). Keep the kernel SRPM,
base_ref, ref, version and config changes in sync on each kernel rebase; check
the patch stack again.

For Mesa, keep Fedora's complete subpackage split and Rust dependency
packaging. Pinning a new source version may require adapting the Meson options,
vendored dependency versions and file lists. A source pin alone is not a build
test.

The aarch64 Mesa build also produces `gravity-flatpak-graphics`, automatically
selected by Flatpak and required by the platform Mesa metapackage. It compiles
the same Mesa source in the pinned freedesktop SDK; binary-build networking must
be enabled for SDK acquisition (`copr-cli build --enable-net on`). See
[gravity-flatpak-graphics](gravity-flatpak-graphics/README.md) for its runtime
layouts, compiler pins and native validation command.

## x86 Mesa for FEX

x86 programs run through FEX need x86_64 and i686 builds of the system Mesa's
source. Every x86 binary in the packages that carry them is built by COPR:

- `mesa-fex-guest` builds the `mesa` entry's source (its `sources.json` entry
  names `"source": "mesa"`, and `tools/package.py` takes its Version and
  Release from `mesa/mesa.spec`) in the `fedora-44-x86_64` chroot. It builds
  x86_64 and, with `-m32` against Fedora's i686 packages from the same
  repositories, i686 Mesa, and assembles the two trees with Fedora's x86
  libraries installed in that build root
  ([mesa-fex-guest/README.md](mesa-fex-guest/README.md)).
- `gravity-x86-mesa` (noarch, built in `fedora-44-aarch64`) carries that RPM
  in its SRPM, fetched from the COPR result directory by the URL and SHA256
  recorded in `sources.json` and `downloads.lock.json`, and installs its
  trees as `gravity-x86-mesa` and `fex-guestos-mesa`. Its Version and Release
  are those of the `mesa-fex-guest` build. It requires `gravity-mesa-revision`
  = the commit both were built from, which `mesa-dri-drivers` provides.

On a Mesa update, change the `mesa` ref and `mesa.spec` as before. After COPR
has built `mesa` and `mesa-fex-guest` from that commit:

```sh
make pin
git diff -- sources.json downloads.lock.json
```

`make pin` asks COPR's public API for the newest successful
`mesa-fex-guest` build of mesa.spec's Version and Release, downloads its
RPM, checks that it was built from the `mesa` ref, and records the URL and
hash. `make status` reports a stale pin, and `make srpm
PACKAGE=gravity-x86-mesa` refuses to use one. For a local test build, pass
the RPM directly: `make srpm PACKAGE=gravity-x86-mesa ARGS='--rpm
path/to/mesa-fex-guest-....x86_64.rpm'`.

## COPR and build order

Use [Git-backed COPR builds](COPR.md) to build directly from GitHub without
uploading local SRPMs. It includes the exact form settings and webhook setup.

Create one project with the `fedora-44-aarch64` and `fedora-44-x86_64`
chroots. Configure that project to make already built packages available to
subsequent builds. Build `mesa-fex-guest` in `fedora-44-x86_64` only (its
spec is `ExclusiveArch: x86_64`) and every other package in
`fedora-44-aarch64` only.

1. Independent: kernel, Mesa, mesa-fex-guest, uboot-tools, gravity-installer,
   gravity-logos, gravity-release, gravity-appstream-metadata,
   gravity-remix-scripts, gravity-x86, gravity-audio-j713, steam.
2. gravity-bootloader after gravity-logos. gravity-x86-mesa after Mesa and
   mesa-fex-guest succeeded and `make pin` was committed.
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
