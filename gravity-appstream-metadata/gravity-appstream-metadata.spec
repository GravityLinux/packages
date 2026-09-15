Name:           gravity-appstream-metadata
Vendor:         Gravity Linux
Version:        20260915
Release:        100.gravity%{?dist}
Summary:        Operating system metadata for Gravity Linux
License:        MIT
URL:            https://gravitylinux.org/
Source0:        org.gravitylinux.metainfo.xml
Source1:        LICENSE
BuildArch:      noarch
BuildRequires:  appstream
Provides:       fedora-appstream-metadata = 1:%{version}-%{release}
Obsoletes:      fedora-appstream-metadata < 1:%{version}-%{release}
Conflicts:      fedora-asahi-remix-appstream-metadata

%description
Operating system metadata for software centers on Gravity Linux.

%prep
cp %{SOURCE1} .

%build

%install
install -Dpm0644 %{SOURCE0} %{buildroot}%{_datadir}/metainfo/org.gravitylinux.metainfo.xml

%check
appstreamcli validate --no-net %{SOURCE0}

%files
%license LICENSE
%{_datadir}/metainfo/org.gravitylinux.metainfo.xml

%changelog
* Tue Sep 15 2026 Gravity Linux maintainers - 20260915-100.gravity
- Initial Gravity operating system metadata
