#!/bin/sh
# A Flatpak SDK is a /usr tree. Running its compiler directly avoids needing
# a session bus or a nested Flatpak installation in mock/COPR.
set -eu
test "$(uname -m)" = aarch64
# Reuse the builder's proc view read-only: nested mock/nspawn containers may
# mask proc entries, preventing an unprivileged child from mounting procfs.
exec bwrap --unshare-all --die-with-parent \
  --ro-bind "$PWD/sdk" /usr \
  --symlink usr/bin /bin --symlink usr/lib /lib --symlink usr/lib /lib64 \
  --symlink usr/sbin /sbin --dev /dev --ro-bind /proc /proc --tmpfs /tmp \
  --dir /etc --dir /run --bind "$PWD" /build --chdir /build \
  --clearenv --setenv PATH /usr/lib/sdk/llvm22/bin:/usr/bin \
  --setenv HOME /tmp --setenv LC_ALL C.UTF-8 \
  /usr/bin/bash /build/build.sh "$1"
