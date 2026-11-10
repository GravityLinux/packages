Name:           gravity-remix-scripts
Vendor:         Gravity Linux
Version:        20260915
Release:        105.gravity%{?dist}
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
Requires:       util-linux-core
Requires:       policycoreutils-python-utils
Conflicts:      fedora-asahi-remix-scripts

%description
Install optional RPMs from the Gravity ESP directory on first boot. Swap is
Fedora's default zram; setup-swap.sh remains as a manual swapfile tool.
Derived from Fedora Asahi Remix first-boot integration.
Temporarily disable system sleep while M4 suspend/resume is unsupported.

%prep
%autosetup

%build

%install
install -Dpm0644 -t %{buildroot}%{_unitdir} gravity-*.service
install -Dpm0644 -t %{buildroot}%{_udevhwdbdir} 65-autosuspend-override-asahi.hwdb
install -Dpm0755 -t %{buildroot}%{_libexecdir}/%{name} install-extras.sh setup-swap.sh
install -Dpm0644 -t %{buildroot}%{_datadir}/%{name} gravity-enable-zswap.conf
install -Dpm0644 -t %{buildroot}%{_tmpfilesdir} 60-gravity-mglru-min-ttl.conf
install -Dpm0644 90-gravity-no-sleep.conf %{buildroot}%{_prefix}/lib/systemd/sleep.conf.d/90-gravity-no-sleep.conf
install -Dpm0644 90-gravity-no-sleep-logind.conf %{buildroot}%{_prefix}/lib/systemd/logind.conf.d/90-gravity-no-sleep.conf
for unit in suspend hibernate hybrid-sleep suspend-then-hibernate; do
    install -Dpm0644 90-gravity-block-sleep-service.conf %{buildroot}%{_unitdir}/systemd-$unit.service.d/90-gravity-no-sleep.conf
done

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
# turned zswap on and put a Btrfs swapfile in fstab. The Gravity kernel
# (kernel-p3s) keeps that swapfile off, so those installs had no swap at all
# after upgrading. Undo exactly what setup-swap.sh wrote, keeping backups;
# zram comes up on the next boot. The swapfile itself stays (unused) under
# /var/swap; a swapfile that is active now stays active until reboot.
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

%preun
%systemd_preun gravity-extras-firstboot.service

%postun
%systemd_postun gravity-extras-firstboot.service

%files
%license LICENSE
%doc SLEEP-POLICY.md SWAP-POLICY.md
%{_unitdir}/gravity-*.service
%{_udevhwdbdir}/65-autosuspend-override-asahi.hwdb
%{_libexecdir}/%{name}/
%{_datadir}/%{name}/
%{_tmpfilesdir}/60-gravity-mglru-min-ttl.conf
%{_prefix}/lib/systemd/sleep.conf.d/90-gravity-no-sleep.conf
%{_prefix}/lib/systemd/logind.conf.d/90-gravity-no-sleep.conf
%dir %{_unitdir}/systemd-suspend.service.d
%dir %{_unitdir}/systemd-hibernate.service.d
%dir %{_unitdir}/systemd-hybrid-sleep.service.d
%dir %{_unitdir}/systemd-suspend-then-hibernate.service.d
%{_unitdir}/systemd-suspend.service.d/90-gravity-no-sleep.conf
%{_unitdir}/systemd-hibernate.service.d/90-gravity-no-sleep.conf
%{_unitdir}/systemd-hybrid-sleep.service.d/90-gravity-no-sleep.conf
%{_unitdir}/systemd-suspend-then-hibernate.service.d/90-gravity-no-sleep.conf

%changelog
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
