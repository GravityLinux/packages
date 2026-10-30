# SPDX-License-Identifier: GPL-2.0-only
# Source this once with native Fedora host CFLAGS; recursive makes inherit it.
# An empty argument preserves caller-supplied host flags for cross builds.
if [ -n "${1-}" ]; then
    HOST_EXTRACFLAGS=$(printf '%s\n' "$1" |
        sed -E 's@-specs=[^[:space:]]*/redhat-annobin-cc1@@g')
else
    HOST_EXTRACFLAGS=${HOST_EXTRACFLAGS-}
fi
export HOST_EXTRACFLAGS
