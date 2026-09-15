# Set only after the packaged artwork has been relicensed and reviewed.
%{!?gravity_artwork_license:%{error:Set gravity_artwork_license after reviewing the artwork license}}
Name:           gravity-logos
Vendor:         Gravity Linux
Version:        20260915
Release:        100.gravity%{?dist}
Summary:        Gravity Linux boot and desktop artwork
License:        %{gravity_artwork_license}
URL:            https://github.com/GravityLinux/artwork
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
Provides:       system-logos
Provides:       system-logos(bootloader)
Conflicts:      fedora-logos

%description
Gravity Linux logos for the bootloader and desktop. Artwork copyright licensing
and Gravity trademarks are separate; consult the source license.

%prep
%autosetup

%build

%install
install -Dpm0644 logos/png_128/GravityLinux_logomark.png %{buildroot}%{_datadir}/pixmaps/bootloader/bootlogo_128.png
install -Dpm0644 logos/png_256/GravityLinux_logomark.png %{buildroot}%{_datadir}/pixmaps/bootloader/bootlogo_256.png
install -Dpm0644 logos/icns/GravityLinux_logomark.icns %{buildroot}%{_datadir}/pixmaps/bootloader/gravity.icns
install -Dpm0644 logos/svg/GravityLinux_logomark.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/gravity-logo-icon.svg
install -Dpm0644 logos/boot_logo.ppm %{buildroot}%{_datadir}/pixmaps/bootloader/boot_logo.ppm

%files
%license README.md logos/licenses/*
%{_datadir}/pixmaps/bootloader/
%{_datadir}/icons/hicolor/scalable/apps/gravity-logo-icon.svg

%changelog
* Tue Sep 15 2026 Gravity Linux maintainers - 20260915-100.gravity
- Package Gravity bootloader and desktop artwork
