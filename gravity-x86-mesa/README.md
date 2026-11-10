# gravity-x86-mesa

x86 Mesa for x86 programs that gravity-x86 runs outside Steam. The Fedora
x86 root filesystem (`fex-emu-rootfs-fedora`) ships Fedora's Mesa, which
finds the Apple GPU but cannot submit work to it (`DRM_IOCTL_ASAHI_SUBMIT`
fails), so GL and Vulkan windows stay blank.

This source package also builds `fex-guestos-mesa`, the x86 tree Steam's FEX
compatibility tool uses (README-fex-guestos-mesa.md).

## How it is used

- This package installs x86_64 (`usr/lib64`) and i686 (`usr/lib`) Mesa under
  `/usr/share/gravity-x86/mesa-x86`, in the same layout as the root
  filesystem.
- gravity-x86's `gravity-x86-rootfs.service` mounts, at boot:
  - the packaged image `/usr/share/fex-emu/RootFS/default.erofs` at
    `/run/gravity-x86/base`;
  - a read-only overlayfs at `/run/gravity-x86/rootfs`, with this tree over
    the image.
- gravity-x86's `/usr/share/fex-emu/Config.json` names that directory as FEX's
  RootFS.

Files at the same path replace Fedora's: libGLX_mesa, libEGL_mesa, libgbm
and `dri_gbm`, the `dri/` loaders, `libvulkan_asahi` and its ICD files, the
glvnd EGL vendor file and `/usr/share/drirc.d`. Fedora's other drivers stay
in place, so Vulkan also lists lavapipe. GL has no llvmpipe fallback, because
the `dri/` loaders now lead to this build, which has only asahi and zink.

## Where it comes from

Nothing is compiled in this package. COPR builds `mesa-fex-guest` in the
`fedora-44-x86_64` chroot from the same Mesa source pin as `mesa`
(`sources.json`); that RPM holds this tree and the guestos tree, assembled
on x86_64. This package's SRPM contains that RPM, fetched from the COPR
result directory by the URL and SHA256 that `make pin` records in
`sources.json` and `downloads.lock.json`, and installs its trees. Version and
Release are those of the `mesa-fex-guest` build.

`Requires: gravity-mesa-revision = <commit>` ties it to the system Mesa built
from the same commit (`mesa-dri-drivers` provides it). Installing the package
remounts the root filesystem (`try-restart`): new x86 programs get the new
Mesa, and running ones keep the old view until they exit.
