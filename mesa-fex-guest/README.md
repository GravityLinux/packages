# mesa-fex-guest

x86_64 and i686 builds of the system Mesa's pinned source (`sources.json`
entry `mesa`), built by COPR in the `fedora-44-x86_64` chroot and assembled
into the two trees x86 programs need on ARM64 Gravity systems:

| Tree (below `/usr/lib/mesa-fex-guest`) | Installed on ARM64 by | Path there |
| --- | --- | --- |
| `gravity-x86/`: Mesa in Fedora's layout (x86_64 in `usr/lib64`, i686 in `usr/lib`) | `gravity-x86-mesa` | `/usr/share/gravity-x86/mesa-x86` |
| `guestos/`: Mesa plus Fedora's x86 glibc, C++ runtime, libglvnd, X11, Wayland and the other libraries it needs, `bash`, `busybox` and `ldconfig`, in an Arch-style layout (x86_64 in `usr/lib`, i686 in `usr/lib32`), with `ld.so.cache` and `graphics_provider.json` | `fex-guestos-mesa` | `/usr/share/guestos/fex-mesa` |

`MANIFEST-gravity-x86.json` and `MANIFEST-guestos.json` name the source of
every file: `mesa:<commit>:<arch>`, `fedora:<NEVRA>` or `generated`.

## Build

- One meson build of the build-machine tools (`mesa_clc`, `vtn_bindgen2`,
  `asahi_clc`), then the x86_64 libraries and the i686 libraries (`-m32`,
  against Fedora's i686 `-devel` packages from the x86_64 repositories).
- The drivers are the Apple GPU GL (asahi) and Vulkan (Honeykrisp) drivers
  and zink, without LLVM at run time, so there is no llvmpipe or lavapipe.
- Compiler and linker flags are Fedora's for each architecture.
- Both library builds search the GBM backend directories of both layouts, so
  the same files serve both trees.
- The guestos tree's Fedora libraries are the packages in
  `guestos-packages.txt`, installed in the build root as build dependencies
  from Fedora's repositories. A rebuild picks up their updates.
- `assemble.py` copies them, checks that every `NEEDED` library is present
  with the right ELF class, and writes `ld.so.cache` itself (the tree's own
  `ldconfig -r` would need root to chroot). The tree's `ldconfig -p` then has
  to list exactly the written entries.

`tools/package.py` takes Version and Release from `mesa/mesa.spec` and the
source commit from `sources.json`, so a Mesa update needs no change here.
