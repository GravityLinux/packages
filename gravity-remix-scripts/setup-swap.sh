#!/usr/bin/sh
set -e

cd "$(dirname "$0")"

size=12G

if [ "$(whoami)" != "root" ]; then
    echo "Script must be run as root" >&2
    exit 1
fi

if [ "$1" == "--recreate" ]; then
    shift
    swapoff /var/swap/swapfile || true
    rm /var/swap/swapfile
elif [ -e /var/swap/swapfile ]; then
    echo "/var/swap/swapfile already exists, use --recreate to recreate" >&2
    exit 1
fi

[ -n "$1" ] && size="$1"

free_bytes="$(($(stat -f --format="%a*%S" /var)))"
size_bytes="$(numfmt --from=auto "$size")"
need=$((2 * $size_bytes))

if [ "$free_bytes" -lt "$need" ]; then
    echo "Not enough free disk space to allocate swap"
    exit 1
fi

[ ! -e /var/swap ] && btrfs subvolume create /var/swap
chattr +C /var/swap
fallocate -l "$size" /var/swap/swapfile
chmod 0600 /var/swap/swapfile

semanage fcontext -a -t var_t -f d '/var/swap' || true
semanage fcontext -a -t swapfile_t -f f '/var/swap/swapfile' || true
restorecon -v -r '/var/swap'

mkswap /var/swap/swapfile
swapon /var/swap/swapfile
# A distinct entry records the administrator's choice; the historical
# first-boot migration in the RPM scriptlet removes only its old exact line.
if grep -qx '/var/swap/swapfile swap swap sw 0 0' /etc/fstab; then
    cp -a /etc/fstab /etc/fstab.rpmsave
    sed -i '\|^/var/swap/swapfile swap swap sw 0 0$|d' /etc/fstab
fi
grep -q '^/var/swap/swapfile[[:space:]]' /etc/fstab || \
    echo '/var/swap/swapfile swap swap defaults,pri=10 0 0' >> /etc/fstab

# Keep Fedora's higher-priority zram and its zswap policy unchanged.
# Disk swap is available immediately and from fstab on subsequent boots.

# Releases before 102 ran this from gravity-setup-swap-firstboot.service; disable it if present.
systemctl disable gravity-setup-swap-firstboot.service 2>/dev/null || true
