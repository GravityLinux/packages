Name:           gravity-repos
Vendor:         Gravity Linux
Version:        44
Release:        100.gravity%{?dist}
Summary:        Gravity Linux RPM repository configuration
License:        MIT
URL:            https://github.com/GravityLinux/packages
Source0:        gravity.repo
Source1:        RPM-GPG-KEY-gravity
Source2:        LICENSE
BuildArch:      noarch
Requires:       fedora-repos
Conflicts:      asahi-repos

%description
Repository configuration and pinned signing key for Gravity Linux.
Fedora's base and updates repositories remain enabled.

%prep
cp %{SOURCE2} .

%build

%install
install -Dpm0644 %{SOURCE0} %{buildroot}%{_sysconfdir}/yum.repos.d/gravity.repo
install -Dpm0644 %{SOURCE1} %{buildroot}%{_sysconfdir}/pki/rpm-gpg/RPM-GPG-KEY-gravity

%files
%license LICENSE
%config(noreplace) %{_sysconfdir}/yum.repos.d/gravity.repo
%{_sysconfdir}/pki/rpm-gpg/RPM-GPG-KEY-gravity

%changelog
* Tue Sep 15 2026 Gravity Linux maintainers - 44-100.gravity
- Initial Gravity repository package
