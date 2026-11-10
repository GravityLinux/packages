# Swap policy

Since release 102.gravity, Gravity uses Fedora's default swap: zram-generator-defaults
creates /dev/zram0 (min(RAM, 8 GiB)) at boot. Fresh installs do not create disk swap and zswap stays
off (the Gravity kernel builds with CONFIG_ZSWAP_DEFAULT_ON unset).

Earlier releases ran gravity-setup-swap-firstboot.service, inherited from Asahi, on
first boot. Its setup-swap.sh made an 8G Btrfs swapfile at /var/swap/swapfile, wrote an
/etc/systemd/zram-generator.conf that disables zram, and linked
/etc/tmpfiles.d/gravity-enable-zswap.conf to turn zswap on. That service is no longer
shipped or preset. Disk swap with native 4K-page processes, x86 programs and
16K-page processes was validated on kernel 7.3.0-514: Btrfs swapfiles and block
swap passed fork, copy-on-write, remapping and swapoff tests with no mismatches.
The old corruption was an earlier kernel bug that has been fixed. The kernel
no longer blocks the swapfile unit or requires a command-line opt-in.

Since release 105.gravity, upgrading the package moves such an install to the default:
%post renames /etc/systemd/zram-generator.conf to .rpmsave and removes the
/etc/tmpfiles.d/gravity-enable-zswap.conf link and the /var/swap/swapfile line in
/etc/fstab (a copy goes to /etc/fstab.rpmsave), each only when it is exactly what
setup-swap.sh wrote. zram is active from the next boot. The swapfile itself stays
unused under /var/swap; delete it (swapoff it first if still active) to reclaim the
space: `swapoff /var/swap/swapfile; btrfs subvolume delete /var/swap`.

setup-swap.sh is still installed under /usr/libexec/gravity-remix-scripts as a manual
tool; nothing runs it automatically. Since release 107.gravity it creates a 12G
Btrfs swapfile by default (or accepts a size argument), activates it immediately,
and adds it to fstab at priority 10 alongside Fedora's higher-priority zram.
It does not disable zram or enable zswap. Run `setup-swap.sh --recreate [size]`
if the unused old swapfile already exists. Its distinct fstab entry survives
subsequent package upgrades. Administrator changes to the old first-boot
configuration are preserved by the exact-match migration; review those manually.

On an unmodified published install, upgrading and rebooting therefore leaves
zram active, zswap off, and the old disk swapfile unused. Removing the kernel
guard does not automatically opt that install back into disk swap. An install
with a manually configured disk swap entry keeps it; removing the guard makes
that entry usable without a boot argument.

## Running out of memory

zram swap means a full machine can thrash instead of OOM-killing. Once RAM and zram are
both full, only file pages remain reclaimable, and the kernel keeps evicting and
re-reading them (program text, Btrfs metadata) for many minutes while every task,
including systemd-oomd and sshd, waits on those reads. Fedora's systemd-oomd only
watches memory pressure per slice, not swap, and it stalls on its own page faults.

Since release 104.gravity, 60-gravity-mglru-min-ttl.conf (tmpfiles.d) sets the
multi-gen LRU's thrashing prevention, /sys/kernel/mm/lru_gen/min_ttl_ms, to 1000.
kswapd then runs the OOM killer when it cannot keep the last second's working set
in memory. On the M4 mini (16 GiB, 8 GiB zram), a browser workload that filled RAM
and zram locked the machine for more than 13 minutes with the default of 0, and was
OOM-killed within seconds with 1000 (2026-11-06). Override it with a file of the same
name in /etc/tmpfiles.d.
