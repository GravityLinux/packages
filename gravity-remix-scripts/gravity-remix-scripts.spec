Name:           gravity-remix-scripts
Vendor:         Gravity Linux
Version:        20260915
Release:        109.gravity%{?dist}
Summary:        Fedora-specific Gravity first-boot utilities
License:        MIT
URL:            https://github.com/GravityLinux/packages
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  systemd-rpm-macros
Requires:       dnf
Requires:       systemd
Requires:       systemd-udev
Requires:       btrfs-progs
Requires:       e2fsprogs
Requires:       grep
Requires:       util-linux-core
Requires:       policycoreutils-python-utils
Conflicts:      fedora-asahi-remix-scripts
# Its J713 overrides undid the no-sleep policy that this package no longer ships.
Obsoletes:      gravity-air-power < 20261104-3

%description
Install optional RPMs from the Gravity ESP directory on first boot. Swap is
Fedora's default zram; setup-swap.sh remains as a manual swapfile tool.
Derived from Fedora Asahi Remix first-boot integration.
Allow suspend-to-idle only on machines whose kernel and board support it.

%prep
%autosetup

%build

%install
install -Dpm0644 -t %{buildroot}%{_unitdir} gravity-*.service
install -Dpm0644 -t %{buildroot}%{_udevrulesdir} 90-gravity-usb4-sleep-inhibit.rules 91-gravity-smc-restart.rules
install -Dpm0644 -t %{buildroot}%{_udevhwdbdir} 65-autosuspend-override-asahi.hwdb
install -Dpm0755 -t %{buildroot}%{_libexecdir}/%{name} install-extras.sh setup-swap.sh smc-restart-quirk
install -Dpm0644 -t %{buildroot}%{_datadir}/%{name} gravity-enable-zswap.conf
install -Dpm0644 -t %{buildroot}%{_tmpfilesdir} 60-gravity-mglru-min-ttl.conf
install -Dpm0755 -t %{buildroot}%{_systemdgeneratordir} gravity-sleep-generator

%post
%systemd_post gravity-extras-firstboot.service
%tmpfiles_create 60-gravity-mglru-min-ttl.conf
# Release 102 dropped gravity-setup-swap-firstboot.service. Remove an enablement
# link left by an install where it never ran (the unit disables itself on success).
if [ $1 -gt 1 ]; then
    rm -f %{_sysconfdir}/systemd/system/multi-user.target.wants/gravity-setup-swap-firstboot.service
fi
# Move installs made before 102 to the default swap (SWAP-POLICY.md). Their
# first boot ran setup-swap.sh, which disabled zram-generator-defaults,
# turned zswap on and put a Btrfs swapfile in fstab. Undo exactly that old
# automatic setup to keep Fedora's zram default, with backups. Disk swap is
# supported; the manual tool now adds it alongside zram with a distinct fstab
# entry that this migration leaves alone. Active swap stays until reboot.
zg=%{_sysconfdir}/systemd/zram-generator.conf
if [ -f $zg ] && [ "$(cat $zg)" = "# disable zram-generator-defaults config in favor of zswap on Apple systems with swap" ]; then
    mv -f $zg $zg.rpmsave
fi
zs=%{_sysconfdir}/tmpfiles.d/gravity-enable-zswap.conf
if [ -L $zs ] && [ "$(readlink $zs)" = "%{_datadir}/gravity-remix-scripts/gravity-enable-zswap.conf" ]; then
    rm -f $zs
fi
if grep -qx '/var/swap/swapfile swap swap sw 0 0' %{_sysconfdir}/fstab 2>/dev/null; then
    cp -a %{_sysconfdir}/fstab %{_sysconfdir}/fstab.rpmsave
    sed -i '\|^/var/swap/swapfile swap swap sw 0 0$|d' %{_sysconfdir}/fstab
fi

%posttrans
# Apply the restart guard to an SMC reboot driver that was bound before this
# package was installed. Image builds have no running udev daemon.
if [ -S /run/udev/control ]; then
    if udevadm control --reload-rules; then
        udevadm trigger --action=bind --subsystem-match=platform --sysname-match=macsmc-reboot || :
        udevadm settle --timeout=10 || :
    fi
fi
# End of the restart guard refresh.

%preun
%systemd_preun gravity-extras-firstboot.service

%postun
%systemd_postun gravity-extras-firstboot.service

%files
%license LICENSE
%doc SLEEP-POLICY.md SWAP-POLICY.md
%{_unitdir}/gravity-*.service
%{_udevrulesdir}/90-gravity-usb4-sleep-inhibit.rules
%{_udevrulesdir}/91-gravity-smc-restart.rules
%{_udevhwdbdir}/65-autosuspend-override-asahi.hwdb
%{_libexecdir}/%{name}/
%{_datadir}/%{name}/
%{_tmpfilesdir}/60-gravity-mglru-min-ttl.conf
%{_systemdgeneratordir}/gravity-sleep-generator

%changelog
* Wed Nov 11 2026 Niklas Sheth <hi@niklassheth.com> - 20260915-109.gravity
- MacBook Air (M4): keep SMC restart and power-off when the kernel's device
  tree connects the trackpad controller's reset line (kernel 7.3.0-519 on the
  13-inch model); the guard stays for kernels without it.
- Apply the guard at once when the package is installed on a running system.

* Tue Nov 10 2026 Niklas Sheth <hi@niklassheth.com> - 20260915-108.gravity
- Detach the SMC reboot driver on the MacBook Air (M4): after a restart or
  power-off through the SMC the trackpad did not work on the next boot.
  Restart uses the watchdog there and Shut Down halts without cutting power;
  other machines keep SMC restart and power-off.

* Tue Nov 10 2026 Niklas Sheth <hi@niklassheth.com> - 20260915-107.gravity
- Document validated disk swap with 4K-page processes; keep zram as default.
- Make the manual swapfile tool add disk swap alongside zram, without
  enabling zswap or writing the old first-boot configuration.

* Tue Nov 10 2026 Niklas Sheth <niklassheth@gmail.com> - 20260915-106.gravity
- Replace the sleep block on every machine with gravity-sleep-generator,
  which masks the sleep targets at boot unless the board and running kernel
  support suspend-to-idle (J713 with CPU power-down in s2idle). Supported
  machines use systemd's and the desktop's default sleep and lid policy.
- Obsolete gravity-air-power, whose runtime overrides undid the old block.
- Block sleep while a USB4 link is up, since the kernel refuses to suspend
  then (gravity-usb4-sleep-inhibit@.service, started by udev).

* Sun Nov 08 2026 Niklas Sheth <niklassheth@gmail.com> - 20260915-105.gravity
- Move installs from before 102 to zram swap: remove the zram-disabling
  /etc/systemd/zram-generator.conf, the zswap tmpfiles link and the
  /var/swap/swapfile fstab line that setup-swap.sh wrote (exact matches only,
  backups as .rpmsave). With kernel-p3s those installs had no swap at all.

* Fri Nov 06 2026 Gravity Linux maintainers - 20260915-104.gravity
- tmpfiles: set /sys/kernel/mm/lru_gen/min_ttl_ms to 1000 so a full RAM+zram
  machine OOM-kills instead of thrashing file pages for many minutes

* Wed Nov 04 2026 Gravity Linux maintainers - 20260915-103.gravity
- logind: drop HandleLidSwitchExternalPower=ignore; it already follows
  HandleLidSwitch (ignore), and the explicit value could not be undone by a
  board drop-in that enables lid suspend (e.g. gravity-air-power on J713)

* Mon Nov 02 2026 Gravity Linux maintainers - 20260915-102.gravity
- Stop creating a Btrfs swapfile and enabling zswap on first boot: drop
  gravity-setup-swap-firstboot.service so fresh installs keep Fedora's default
  zram swap (zram-generator-defaults); setup-swap.sh remains a manual tool

* Fri Sep 18 2026 Gravity Linux maintainers - 20260915-101.gravity
- Ship removable vendor policy disabling unsupported system sleep
- Block sleep services without leaving persistent administrator masks

* Tue Sep 15 2026 Gravity Linux maintainers - 20260915-100.gravity
- Derive Gravity swap and extras integration from Asahi
