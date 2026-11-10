# gravity-x86

x86 programs on P3S kernels (ARM64 with per-process 4K pages) run through
Fedora's own `binfmt-dispatcher` and `fex-emu`. This package adds:

- `zzz-gravity-x86-x86{,_64}.conf`: binfmt_misc rules sorted after
  binfmt-dispatcher's `zz-` rules, so they take precedence. They start
  `/usr/libexec/gravity-x86/fex-4k`, which requests 4K pages with the
  `ADDR_PAGE_SIZE_4KB` personality bit and, once the kernel has granted them,
  execs `FEXInterpreter` on the executable's pathname (taken from AT_EXECFD,
  then closed). FEX and everything it starts inherit the 4K request. The
  guest's argv0 is that pathname: FEX takes no separate argv0.
- Without P3S, for setuid/setgid/capability executables, or without AT_EXECFD,
  the launch goes to `binfmt-dispatcher` unchanged, which keeps its muvm
  behaviour. The dispatcher is not used on the 4K path: it reads the
  executable from fd 3, which is stale when one x86 program execs another
  (it relaunched the first program in a loop), and it passes the filename and
  original argv0 to FEX as extra guest arguments.
- `gravity-x86-rootfs.service`: at boot, mounts the packaged
  `fex-emu-rootfs-fedora` image at `/run/gravity-x86/base` and a read-only
  overlayfs at `/run/gravity-x86/rootfs` that puts gravity-x86-mesa's x86 Mesa
  over it. The image's own Fedora Mesa cannot submit work to the Apple GPU.
  The service is restarted when either package is updated; running x86
  programs keep their old view until they exit.
- `/usr/share/fex-emu/Config.json`: FEX's global configuration, naming
  `/run/gravity-x86/rootfs` as the RootFS. FEX starts its own per-user
  FEXServer. A user's `~/.fex-emu/Config.json` or `FEX_ROOTFS` takes
  precedence.

Steam is not involved; the native ARM64 Steam client and its Proton are
packaged separately (steam-gravity).
