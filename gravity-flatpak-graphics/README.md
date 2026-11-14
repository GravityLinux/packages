# Gravity Flatpak graphics

`gravity-flatpak-graphics` is an **aarch64 subpackage of mesa**, not a separate
Mesa source pin or a repacked prebuilt build. Rebuilding Mesa rebuilds it. Its exact
`gravity-mesa-revision` dependency prevents installing a different source commit.
`gravity-platform-metapackage-mesa` pulls it in on an ordinary upgrade.

The RPM owns unmanaged extensions at:

| ID | Branch | Mounted prefix |
| --- | --- | --- |
| org.freedesktop.Platform.GL.host | 25.08 | /usr/lib/aarch64-linux-gnu/GL/host |
| org.freedesktop.Platform.GL.host | 26.08 | /usr/lib/aarch64-linux-gnu/GL/host |
| org.fedoraproject.Platform.GL.host | f45 | /usr/lib64/GL/host |

Flatpak automatically activates `host`. KDE runtimes inherit the corresponding
freedesktop extension point. There is no environment file or app override.
Running applications must be restarted after an upgrade. RPM replaces the files;
relative RUNPATHs and absolute ICD paths accommodate an existing Flatpak loader
cache. Hardware rendering remains the default. Explicit software GL requests
(including a saved `LIBGL_ALWAYS_SOFTWARE=1` application override) use this
extension's llvmpipe. Vulkan software rendering uses the runtime's lavapipe ICD.

This takes the unmanaged `GL.host` layout, metadata links and stale-cache
workaround from Fedora Asahi's mesa-asahi-flatpak packaging.

llvmpipe uses the pinned SDK's existing LLVM 22.1.8 shared library.
It is a prebuilt Flathub compiler library redistributed with this RPM, under
Apache-2.0 WITH LLVM-exception (license text included). `llvm-origin.json` records
its origin, SDK commit and original checksum; each slot's `gravity-build.json`
retains this information. The three slots hardlink one `libLLVM.so.22.1` payload.
LLVM is not built from source on each Mesa build. No other LLVM library or tool
is shipped. The runtime supplies its ordinary library dependencies.

The SDK library is copied byte-for-byte, with its installed checksum equal to
the verified input checksum. It is mode 0644 so Fedora's debuginfo extractor
leaves this prebuilt DSO untouched. The spec tolerates its missing GNU build ID;
Mesa's RUNPATH finds it, and the runtime supplies its dependencies. In the local
extension-only path, redundant RPM stripping is disabled because the assembler
already strips Mesa and preserves LLVM.

## Native source build

The SRPM contains Mesa and pinned supporting source dependencies, plus the SDK
acquisition script and lock files. The binary builder needs network access:
`copr-cli build --enable-net on`. No prebuilt Gravity Mesa is downloaded or
carried in the SRPM.

During `%build`, `export-sdk.py` downloads the two pinned **aarch64 compiler
SDK refs** in `sdk.lock.json` into a temporary private Flatpak installation. It
normalizes an SDK sysroot archive, verifies the uncompressed tar's `sdk.sha256`, then extracts it as
the compiler environment. The downloader never uses or changes a developer's
normal Flatpak installation. Unreachable Flathub, unavailable pinned commits,
invalid signatures or a hash mismatch fail the build before compiling Mesa.
The descriptor fetch has a two-minute timeout; each SDK install/update has a
90-minute bound (a cold download can be slow). Compression differences
between host zlib versions do not change the pinned contents hash.
Updating a moving SDK branch cannot silently change the build tools.

Bubblewrap then mounts this SDK as `/usr`, disconnects networking and compiles
SPIRV-Tools, the LLVM/SPIR-V translator, Mesa's shader tools and the graphics libraries from the SRPM's sources. No session bus, system-wide SDK installation
or qemu is involved. The SDK is a binary compiler dependency; its LLVM shared library is also
redistributed for llvmpipe, with its origin and license recorded as above.
Gravity Mesa itself is built from source.

The oldest supported freedesktop SDK (25.08) sets the ABI baseline for all
three runtime targets; Fedora's different library paths are compiled separately.
The result is tested in 25.08, 26.08 and Fedora f45. This uses one SDK plus its
LLVM extension, rather than three SDK downloads and three toolchain builds.
The runtime's libdrm and other libraries provide the compatible runtime ABI;
Fedora host libraries are never copied into the extension.

For native extension-only validation, `rpmbuild --rebuild --with flatpak_only`
builds the actual subpackage from the SRPM while skipping the host drivers.
The normal build does both. The revision dependency permits testing against an
already installed host Mesa from that source commit at an earlier RPM release.

```sh
make srpm PACKAGE=mesa
mock -r fedora-44-aarch64 --enable-network --with=flatpak_only \
  --rebuild 'dist/mesa-26.3.0~devel-112.gravity.fc44.src.rpm'
```

Allow several GiB of builder scratch space for the SDK repository, deployment,
normalized archive, compiler sysroot and Mesa build. Source preparation no
longer needs an SDK or a large binary source input.

When deliberately updating the toolchain, review the public SDK commits,
export with this script, review the archive hash and update both lock files:

```sh
python3 gravity-flatpak-graphics/export-sdk.py --output /var/tmp/sdk.tar.gz
gzip -dc /var/tmp/sdk.tar.gz | sha256sum
```

Do not bypass a hash mismatch. `downloads.lock.json` separately pins every
source dependency. Mesa comes solely from the `mesa` entry in `sources.json`.

## Release sequence

Build `mesa` in `fedora-44-aarch64`; its outputs include this RPM. Build the
metapackage afterward. Keep the project's manual publication mode enabled until
the complete dependency transaction and runtime tests pass, then regenerate the
repository once. Use the per-build `--enable-net on` switch; no SDK RPM repository or persistent
project-wide networking change is needed.

On Mesa updates, continue the existing mesa-fex-guest / gravity-x86-mesa build
and pin sequence documented in `../COPR.md`. This subpackage adds no second
source pin and requires no post-build binary-payload upload.
