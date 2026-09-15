%global pypi_name gravity_firmware
%global debug_package %{nil}
%if 0%{?__isa_bits} == 32
%global libsymbolsuffix %{nil}
%else
%global libsymbolsuffix ()(64bit)
%endif
Name:           gravity-installer
Vendor:         Gravity Linux
Version:        0.9.1
Release:        100.gravity%{?dist}
Summary:        Gravity Linux firmware extraction tools
License:        MIT
URL:            https://github.com/GravityLinux/installer
Source0:        %{name}-%{version}.tar.gz
BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros
BuildRequires:  python3dist(setuptools)
BuildRequires:  python3dist(asn1)
ExcludeArch:    s390x

%description
Linux firmware tools from the Gravity installer. The macOS installer bundle is
a separate release asset built by installer/build.sh. No extracted Apple vendor
firmware is distributed in this package.

%package -n python3-%{pypi_name}
Summary:        Gravity Linux firmware tools
Requires:       liblzfse.so.1%{libsymbolsuffix}
Requires:       python3dist(asn1)
Requires:       tar
Conflicts:      python3-asahi_firmware

%description -n python3-%{pypi_name}
Extract and install machine-specific firmware using gravity-fwextract.

%prep
%autosetup
# Use Fedora's ASN.1 module, as in Fedora installer packaging.
rm %{pypi_name}/asn1.py

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files %{pypi_name}

%check
%pyproject_check_import

%files -n python3-%{pypi_name} -f %{pyproject_files}
%license LICENSE
%doc README.md
%{_bindir}/gravity-fwextract

%changelog
* Tue Sep 15 2026 Gravity Linux maintainers - 0.9.1-100.gravity
- Package the Gravity Linux firmware consumer
