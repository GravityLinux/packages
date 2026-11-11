# Source of Proton (ARM64, Gravity)

The steam launcher downloads `proton-gravity-arm64-11.0-2e-1.tar.zst` at the
first start (URL, size and SHA-256 in `fetch-client`) and unpacks it as the
compatibility tool `proton-gravity-arm64`. The archive is a build of Valve's
Proton for AArch64 with two changes. It is not built by this package.

## Revisions

- Proton: https://github.com/ValveSoftware/Proton, tag `proton-11.0-2e`,
  commit `bc896217ffcd67f892f952b010f898fe7bd0f0a1`, with its submodules at
  the commits that tag records, except:
- Wine (`wine/`, https://github.com/ValveSoftware/wine): tag
  `proton-wine-11.0-2e` plus `proton-wine-ntdll-header-only-sve-context.patch`.
  On CPUs with SME but without SVE (Apple M4), Linux puts an SVE record
  without register storage into signal frames; Wine wrote predicate registers
  past it and the kernel rejected the signal return, so no Windows program
  started.
- FEX (`FEX/`, https://github.com/FEX-Emu/FEX): tag `FEX-2607` plus
  `proton-FEX-upstream-681636cd.patch`, which is upstream commit
  `681636cd68ea7d7083635479a9211651dcec6d07` unchanged.

The build reports itself as `proton-11.0-2e-2-g3233a3a`: the two commits
after the tag only move the Wine and FEX submodules to these revisions.

## Build

Proton builds in Valve's SDK container; see Proton's README. This build used
the image `registry.gitlab.steamos.cloud/proton/steamrt4/sdk/arm64-llvm:4.0.20260331.220802-2`
on an AArch64 machine:

```sh
git clone --recurse-submodules --branch proton-11.0-2e https://github.com/ValveSoftware/Proton.git proton
git -C proton/wine am ../../proton-wine-ntdll-header-only-sve-context.patch
git -C proton/FEX am ../../proton-FEX-upstream-681636cd.patch
mkdir build && cd build
../proton/configure.sh --target-arch=arm64 --build-name=proton-gravity-arm64
make redist
```

`redist/` is the tool directory that the archive holds. The launcher adds
its own `compatibilitytool.vdf` (tool name `proton-gravity-arm64`, shown as
"Proton (ARM64, Gravity)") and `NOTICE.txt`.

Proton's build downloads further inputs itself: the wine-gecko 2.47.4,
wine-mono 11.2.0 and xalia 0.4.9 release archives named in its `Makefile.in`,
and, through piper's CMake files, espeak-ng, piper-phonemize, fmt, spdlog and
onnxruntime. Their sources are published by those projects at the versions
named there.

## Licences

Proton's own files are BSD-3-Clause; Wine, vkd3d-proton, GStreamer and FFmpeg
are LGPL; espeak-ng is GPL-3.0-or-later; wine-gecko is MPL-2.0; the other
components carry the licences listed in the tool's `LICENSE` file. The
Steamworks SDK headers in Proton's `lsteamclient` directory are under Valve's
Steamworks SDK licence.
