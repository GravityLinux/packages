Name:           gravity-repos-experimental
Vendor:         Gravity Linux
Version:        44
Release:        100.gravity%{?dist}
Summary:        Opt-in Gravity Linux experimental repository
License:        MIT
URL:            https://github.com/GravityLinux/packages
Source0:        gravity-experimental.repo
Source1:        LICENSE
BuildArch:      noarch
Requires:       gravity-repos

%description
Enable the Gravity experimental COPR alongside the stable repository.
Both repositories use priority 10, so newer RPM versions are preferred.

%prep
cp %{SOURCE1} .

%build

%install
install -Dpm0644 %{SOURCE0} %{buildroot}%{_sysconfdir}/yum.repos.d/gravity-experimental.repo

%files
%license LICENSE
%config(noreplace) %{_sysconfdir}/yum.repos.d/gravity-experimental.repo

%changelog
* Thu Oct 29 2026 Gravity Linux maintainers - 44-100.gravity
- Add the opt-in experimental repository
