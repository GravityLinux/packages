Name:           gravity-remix-scripts
Vendor:         Gravity Linux
Version:        20260915
Release:        101.gravity%{?dist}
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
Install optional RPMs from the Gravity ESP directory and configure swap on first
boot. Derived from Fedora Asahi Remix first-boot integration.
Temporarily disable system sleep while M4 suspend/resume is unsupported.

%prep
%autosetup

%build

%install
install -Dpm0644 -t %{buildroot}%{_unitdir} gravity-*.service
install -Dpm0644 -t %{buildroot}%{_udevhwdbdir} 65-autosuspend-override-asahi.hwdb
install -Dpm0755 -t %{buildroot}%{_libexecdir}/%{name} install-extras.sh setup-swap.sh
install -Dpm0644 -t %{buildroot}%{_datadir}/%{name} gravity-enable-zswap.conf
install -Dpm0644 90-gravity-no-sleep.conf %{buildroot}%{_prefix}/lib/systemd/sleep.conf.d/90-gravity-no-sleep.conf
install -Dpm0644 90-gravity-no-sleep-logind.conf %{buildroot}%{_prefix}/lib/systemd/logind.conf.d/90-gravity-no-sleep.conf
for unit in suspend hibernate hybrid-sleep suspend-then-hibernate; do
    install -Dpm0644 90-gravity-block-sleep-service.conf %{buildroot}%{_unitdir}/systemd-$unit.service.d/90-gravity-no-sleep.conf
done

%post
%systemd_post gravity-extras-firstboot.service gravity-setup-swap-firstboot.service

%preun
%systemd_preun gravity-extras-firstboot.service gravity-setup-swap-firstboot.service

%postun
%systemd_postun gravity-extras-firstboot.service gravity-setup-swap-firstboot.service

%files
%license LICENSE
%doc SLEEP-POLICY.md
%{_unitdir}/gravity-*.service
%{_udevhwdbdir}/65-autosuspend-override-asahi.hwdb
%{_libexecdir}/%{name}/
%{_datadir}/%{name}/
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
* Fri Sep 18 2026 Gravity Linux maintainers - 20260915-101.gravity
- Ship removable vendor policy disabling unsupported system sleep
- Block sleep services without leaving persistent administrator masks

* Tue Sep 15 2026 Gravity Linux maintainers - 20260915-100.gravity
- Derive Gravity swap and extras integration from Asahi
