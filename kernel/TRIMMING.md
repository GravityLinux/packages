# Apple 16K kernel scope

gravity-trim.config is applied only to the normal and debug AArch64 16K
configs, after gravity.config. Other Fedora variants are unchanged.

We exclude non-Apple GPU drivers (including discrete/eGPU drivers) and unrelated
ARM SoC families. Keep ARCH_APPLE, both Asahi GPU drivers, DCP, Apple storage,
radio and audio drivers, generic PCI/NVMe, USB/HID/audio/network/storage, SCSI,
filesystems, networking and virtio/QEMU support. Power management remains in
the kernel; unsupported sleep is controlled by an independently updatable RPM.

Use CONFIG_SYMBOL=n entries in the fragments: the packaging overlay parser
emits canonical `# CONFIG_SYMBOL is not set` entries for Fedora's comparator.
It does not interpret commented-out input assignments. Regenerate with the
pinned source and Fedora's dummy-toolchain method, checking listnewconfig
before olddefconfig for BOTH 16K variants. This catches options that become
visible after removing a selecting driver (such as SND_SOC_RT5640).

Run the overlay regression test from the repository root:

    PYTHONPATH=tools python3 -m unittest discover -s tools -p test_kernel_configs.py

Check all AArch64 variants against the extracted baseline SRPM configs, using
the actual Fedora mismatch comparator (in addition to listnewconfig):

    python3 tools/check_kernel_kconfig.py /path/to/pinned/linux /path/to/SOURCES

Both inputs are read-only; generation takes place in a temporary build directory.

Config checks are not a full kernel build or a hardware test. Re-test boot,
graphics, radios and external peripherals after changing the fragment.
