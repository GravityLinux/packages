Name:           gravity-remix-scripts
Vendor:         Gravity Linux
Version:        20260915
Release:        100.gravity%{?dist}
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

%prep
%autosetup

%build

%install
install -Dpm0644 -t %{buildroot}%{_unitdir} gravity-*.service
install -Dpm0644 -t %{buildroot}%{_udevhwdbdir} 65-autosuspend-override-asahi.hwdb
install -Dpm0755 -t %{buildroot}%{_libexecdir}/%{name} install-extras.sh setup-swap.sh
install -Dpm0644 -t %{buildroot}%{_datadir}/%{name} gravity-enable-zswap.conf

%post
%systemd_post gravity-extras-firstboot.service gravity-setup-swap-firstboot.service

%preun
%systemd_preun gravity-extras-firstboot.service gravity-setup-swap-firstboot.service

%postun
%systemd_postun gravity-extras-firstboot.service gravity-setup-swap-firstboot.service

%files
%license LICENSE
%{_unitdir}/gravity-*.service
%{_udevhwdbdir}/65-autosuspend-override-asahi.hwdb
%{_libexecdir}/%{name}/
%{_datadir}/%{name}/

%changelog
* Tue Sep 15 2026 Gravity Linux maintainers - 20260915-100.gravity
- Derive Gravity swap and extras integration from Asahi
