# Swap policy

Since release 102.gravity, Gravity uses Fedora's default swap: zram-generator-defaults
creates /dev/zram0 (min(RAM, 8 GiB)) at boot. There is no disk swap and zswap stays
off (the Gravity kernel builds with CONFIG_ZSWAP_DEFAULT_ON unset).

Earlier releases ran gravity-setup-swap-firstboot.service, inherited from Asahi, on
first boot. Its setup-swap.sh made an 8G Btrfs swapfile at /var/swap/swapfile, wrote an
/etc/systemd/zram-generator.conf that disables zram, and linked
/etc/tmpfiles.d/gravity-enable-zswap.conf to turn zswap on. That service is no longer
shipped or preset. A Btrfs swapfile under the M4 4K-process (P3S) kernels is not
validated: a swap test on the root Btrfs corrupted a test machine (2026-10-26).

Since release 105.gravity, upgrading the package moves such an install to the default:
%post renames /etc/systemd/zram-generator.conf to .rpmsave and removes the
/etc/tmpfiles.d/gravity-enable-zswap.conf link and the /var/swap/swapfile line in
/etc/fstab (a copy goes to /etc/fstab.rpmsave), each only when it is exactly what
setup-swap.sh wrote. zram is active from the next boot. The swapfile itself stays
unused under /var/swap; delete it (swapoff it first if still active) to reclaim the
space: `swapoff /var/swap/swapfile; btrfs subvolume delete /var/swap`.

setup-swap.sh is still installed under /usr/libexec/gravity-remix-scripts as a manual
tool; nothing runs it.

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
