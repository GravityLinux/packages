# Packaging provenance

Imported on 2026-09-15. Upstream copyright and license notices are retained.
The top-level MIT license applies to new packaging code; it does not relicense
the source projects, patches, or artwork.

| Directory | Upstream | Pinned packaging revision |
| --- | --- | --- |
| kernel | Asahi kernel source build 10979408 | kernel-7.1.13-403.asahi.fc44.src.rpm |
| mesa | https://src.fedoraproject.org/rpms/mesa (f44) | 63150cfc593fcc41d67c5a1b720cc2065a1cf00d |
| m1n1 | https://src.fedoraproject.org/rpms/m1n1 (f44) | 11a3eafd7658f7adc27859b1f89f7e47db4791a5 |
| gravity-scripts | https://src.fedoraproject.org/rpms/asahi-scripts (f44) | 50aa8f51e8ad9a7a72f70ced85737f76038e143c |
| uboot-tools | https://forge.fedoraproject.org/asahi/uboot-tools | cc0fd17aff5dbaeff0ff7e6026ae4acdeaa2d2c9 |
| gravity-platform-metapackage | https://forge.fedoraproject.org/asahi/asahi-platform-metapackage | a44fe5345078565b1648db6e469680eb7275bc48 |
| gravity-remix-scripts | https://forge.fedoraproject.org/asahi/fedora-asahi-remix-scripts | 63eac2ef484f94cad6a00128a533b4c9a1b77cfa |
| gravity-release | https://forge.fedoraproject.org/asahi/fedora-asahi-remix-release | 588451630a9e35cd6d4fe59f86aa6ec9e43d05d6 |

The installer spec follows Fedora's asahi-installer Linux firmware subpackage
layout. It intentionally does not bundle the macOS Python/libffi runtime or
build the macOS installer archive inside COPR.

## U-Boot

The package retains the Fedora/Asahi tools and patch series. Starting with
201.gravity, the AArch64 board list is restricted to apple_m1 to shorten builds;
firmware build dependencies used only by other AArch64 boards are omitted.
The imported packaging stops at dbd2154cb0d; four additional Asahi NVMe fixes
(01e7f95a992, 6bfd8a4fa84, 2495a9f2ddf, ec49c9d70e6) bring it to
asahi-v2026.07-2 before the Gravity patches.
These committed Gravity patches follow that series:

- 11da9618ef1 — use the Gravity EFI system partition property.
- 9b06f6cddc9 — T8132 memory map.
- 49840d57974 — T8132 ANS2 NVMe.
- 2db9584de33 — find the ESP on T8132 NVMe.
- 61d4b40d3fa — service RTKit messages while waiting for the controller.
- 4b738f4f51b — hold ANS reset during controller removal.
- ddecfb8eb6a — record the tested 32-bank Apple memory configuration.
- 6e594cafea8 — inject per-radio Bluetooth calibration from the ESP.
- a2f6913694f — inject Wi-Fi calibration through the same bounded loader.

The packaged Gravity U-Boot revision on `gravity-alpha-20260925` is
`a2f6913694ff26908c16948af3f8372429782263` (RPM release 203.gravity).
Re-export the patches and update this file when that source changes.

## Kernel

Baseline source:
https://download.copr.fedorainfracloud.org/results/@asahi/kernel/srpm-builds/10979408/kernel-7.1.13-403.asahi.fc44.src.rpm

SHA256:
`b21403621e44d6390c089126afb2c8ee41a9926b4bd7a840b544b39ffd15be9a`

That COPR build's overall state is failed; using its source packaging does not
establish a successful binary build. Gravity must pass its own aarch64 build.

The Gravity patch is generated against the Asahi source revision
`3988dac1664c05fa7c8310fcad8eee10428b5f43`, with both endpoints recorded in
sources.json. The baseline source tarball and Fedora/Asahi patch are preserved.
No source archive is committed to this repo.
The generated diff uses two context lines to avoid overlapping Fedora's
adjacent iomfb-surfaces fix in dcp_platform_probe. Both changes are retained.

## gravity-bootloader (upstream m1n1)

Gravity's package is named `gravity-bootloader`; its repository remains `bootloader`:
https://github.com/GravityLinux/bootloader. Upstream binary and runtime paths
retain their m1n1 names for boot-chain compatibility.

The selected M4 fork carries GPL-2.0-only contributions in addition to upstream
MIT code and vendored dependencies. The spec includes both LICENSE.GPL2 and
LICENSE.MIT. Its upstream artwork submodule is omitted from source snapshots:
the Makefile uses checked-in binary logo data, and the package supplies its
external boot logo from gravity-logos. This is the same external-logo mechanism
used by Fedora's packaging.
