#!/bin/sh
# SPDX-License-Identifier: MIT

set -e

GRUB_CFG="/boot/grub2/grub.cfg"
GRUB_ENV="/boot/grub2/grubenv"

GRUB_DEF="${1:-/etc/default/grub}"

if [ ! -f "${GRUB_DEF}" ]; then
    echo "\"${GRUB_DEF}\" is not a regular file"
    exit 1
fi

# the date if image creation is more important but the fedora version is shorter
# SHA256_F38 from fedora-38-kde-202308291600
# SHA256_F39A from fedora-39-kde-202401071600
# SHA256_F39B from fedora-39-kde-202404071600
# SHA256_F40 from fedora-40-kde-202407011600
# SHA256_F42 from fedora-42-kde-202504171600

SHA256_F38="e0e9f98daa3cd60c009457b7f7edcba0613a5e29bb47ff007a4da9a2131c54bb" # TIMEOUT=5
SHA256_F39A="18b3f46a5df602be9225642f70f577774aec0fe29889fb5ae45734f65d0d0626" # TIMEOUT=1
SHA256_F39B="bd8bcc2fd4c87a7e3cda6baf6e0b58077232177c77bcb30c3daa2e61997a543d" # TERMINAL_{INPUT,OUTPUT}
SHA256_F40="c0b8c0a85add76951e27a028f004615ed50429db76e71733b6520951ff0cd64b" # -GRUB_ENABLE_BLSCFG=true
SHA256_F42="abee34c21b1e42d6edadb340fb0872a85eabd20fa957a31965ba8aaac002ceda" # +GRUB_DISABLE_OS_PROBER=true

SHA256_CUR=$(sha256sum "${GRUB_DEF}" | cut -d' ' -f1)

if [ $SHA256_CUR != $SHA256_F38 -a \
     $SHA256_CUR != $SHA256_F39A -a \
     $SHA256_CUR != $SHA256_F39B -a \
     $SHA256_CUR != $SHA256_F40 -a \
     $SHA256_CUR != $SHA256_F42 ]; then
    echo "\"${GRUB_DEF}\" was modified, skip fixups."
    exit 0
fi

# always delete "GRUB_TIMEOUT_STYLE=hidden" and "GRUB_GFXMODE=auto"
SED_CMD="/GRUB_TIMEOUT_STYLE=hidden/d
/GRUB_GFXMODE=auto/d
"

# disable OS_PROBER, it's a bad fit for Apple Silicon setups
if [ $SHA256_CUR != $SHA256_F42 ]; then
    SED_CMD+="/GRUB_DISABLE_RECOVERY/a\
GRUB_DISABLE_OS_PROBER=true
"
fi

# add missing GRUB_ENABLE_BLSCFG=true
if [ $SHA256_CUR = $SHA256_F40 -o $SHA256_CUR = $SHA256_F42 ]; then
    SED_CMD+="/GRUB_DISTRIBUTOR/a\
GRUB_ENABLE_BLSCFG=true
"
fi

if [ $SHA256_CUR != $SHA256_F38 ]; then
    SED_CMD+="s/\(GRUB_TIMEOUT\)=1/\1=5/
"
fi

# exit without modifications for test runs
if [ "${GRUB_DEF}" != "/etc/default/grub" ]; then
    echo "Adjusted grub2 defaults:"
    sed -e "${SED_CMD}" < "${GRUB_DEF}"
    exit 0
fi

# check all prerequisites before modification so the script may be executed again
if [ ! -f "${GRUB_CFG}" ]; then
    echo "Error: \"${GRUB_CFG}\" does not exists"
    exit 1
elif [ ! -f "${GRUB_ENV}" ]; then
    echo "Error: \"${GRUB_ENV}\" does not exists"
    exit 1
elif [ ! -x /usr/sbin/grub2-mkconfig ]; then
    echo "Error: \"/usr/sbin/grub2-mkconfig\" is not executable"
elif [ ! -x /usr/bin/grub2-editenv ]; then
    echo "Error: \"/usr/bin/grub2-editenv\" is not executable"
fi

echo "Adjust grub defaults to Fedora defaults"
sed -i -e "$SED_CMD" "${GRUB_DEF}"

# Regenerate grub.cfg
echo "Regenerating \"${GRUB_CFG}\""
/usr/sbin/grub2-mkconfig -o "${GRUB_CFG}"

# switch to menu_auto_hide
echo "Adding \"menu_auto_hide=1\" to \"${GRUB_ENV}\""
/usr/bin/grub2-editenv "${GRUB_ENV}" set menu_auto_hide=1
