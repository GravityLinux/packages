# Apple 16K kernel configuration

The kernel package builds Fedora's kernel-7.3.3-200.fc44 configurations. The
fragments here are applied by tools/package.py when it prepares the SRPM:

- gravity-aarch64.config: every AArch64 variant. The DockChannel early
  console, and the options Gravity's source adds, at their Kconfig defaults, so
  Fedora's %prep check finds no unset options in the variants Gravity does not
  ship (stock 4K, debug, RT).
- gravity-other.config: every non-AArch64 Fedora variant (x86_64, ppc64le,
  riscv64, s390x), which %prep processes as well: the few options Gravity's
  source adds outside Apple-only menus, all off.
- gravity.config: the normal and debug AArch64 16K variants, after the above.
  What the M4 needs on top of Fedora: P3S (47-bit VA, no AArch32 compat), and
  the Apple platform, storage, GPU, display, sound and USB drivers built in. It
  was generated against the configuration of the tested 7.3.0-513 kernel:
  every option that kernel enables is enabled here, Apple and boot-critical
  ones stay built in, and generic drivers stay modules as Fedora has them.
  Deliberate differences from 513: no GCC plugins (513 enabled the framework
  but no plugin); Fedora's Rust binder instead of the C binder and its
  binderfs; Fedora's module signing key type; debuginfo and BTF; Fedora's
  choice of kmalloc partitioning where the compiler offers one. The debug
  variant uses KASAN with GCC, which rules out Rust there, so it has no Asahi
  GPU, AOP, SEP or PMP drivers.
- gravity-trim.config: the 16K variants only, last. Non-Apple GPU drivers
  (including discrete/eGPU drivers) and unrelated ARM SoC families are
  excluded. Generic PCI/NVMe, USB/HID/audio/network/storage, SCSI, filesystems,
  networking and virtio/QEMU support stay.

Use CONFIG_SYMBOL=n entries in the fragments: the packaging overlay parser
emits canonical `# CONFIG_SYMBOL is not set` entries for Fedora's comparator.
It does not interpret commented-out input assignments. List every option that
becomes visible through a fragment (Fedora's %prep fails on new options),
checking listnewconfig before olddefconfig for BOTH 16K variants. Options that
are only selected (no prompt) need no entry.

Run the overlay regression test from the repository root:

    PYTHONPATH=tools python3 -m unittest discover -s tools -p test_kernel_configs.py

Check every variant of every architecture against the extracted baseline SRPM configs, using
the actual Fedora mismatch comparator (in addition to listnewconfig). The
Linux tree must be the pinned source with Fedora's patch and the Gravity patch
applied (as %prep does), and Makefile.rhelver from the SRPM in its top level:

    python3 tools/check_kernel_kconfig.py /path/to/patched/linux /path/to/SOURCES

Both inputs are read-only; generation takes place in a temporary build directory.

Config checks are not a full kernel build or a hardware test. Re-test boot,
graphics, radios and external peripherals after changing the fragments.
