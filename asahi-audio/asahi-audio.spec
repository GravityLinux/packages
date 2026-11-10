Name:           asahi-audio
Version:        4.1
Release:        101.gravity%{?dist}
Vendor:         Gravity Linux
Summary:        PipeWire DSP profiles for Apple Silicon machines
License:        MIT
URL:            https://github.com/AsahiLinux/asahi-audio
Source:         %{url}/archive/v%{version}/%{name}-%{version}.tar.gz
# Gravity: J713 (MacBook Air 13", M4) uses the J413 graph, like the J613
Patch:          0001-Add-the-J713-MacBook-Air-13-M4-as-an-alias-of-the-J413.patch
# Gravity: J713 mics use the J413 mic graph, like the J613
Patch:          0002-Add-the-J713-mics-as-an-alias-of-the-J413-mic-graph.patch

BuildArch:      noarch

BuildRequires:  make
Requires:       pipewire >= 1.0
Requires:       wireplumber >= 0.5.1-2
Requires:       pipewire-module-filter-chain-lv2
Requires:       lsp-plugins-lv2 >= 1.2.13-2
Requires:       lv2-bankstown >= 1.1.0
Requires:       lv2-triforce >= 0.2.0
Recommends:     speakersafetyd
Provides:       gravity-asahi-audio = %{version}-%{release}

%description
PipeWire and WirePlumber DSP profiles and configurations to
drive the speaker arrays in Apple Silicon laptops and desktops.

%prep
%autosetup -p1

%build
%make_build

%install
%make_install PREFIX=%{_prefix} DATA_DIR=%{_datadir}

%files
%license LICENSE
%doc README.md
%{_datadir}/asahi-audio/
%{_datadir}/wireplumber/scripts/device/asahi-lock-volume.lua
%{_datadir}/wireplumber/wireplumber.conf.d/99-asahi.conf
%{_datadir}/pipewire/pipewire.conf.d/99-asahi.conf
%{_datadir}/pipewire/pipewire-pulse.conf.d/99-asahi.conf

%changelog
* Sun Nov 08 2026 Niklas Sheth <niklassheth@gmail.com> - 4.1-101.gravity
- J713 internal mics use the J413 mic graph

* Sun Nov 08 2026 Niklas Sheth <niklassheth@gmail.com> - 4.1-100.gravity
- Rebase on Fedora's asahi-audio 4.1 package
- Add the J713 (MacBook Air 13", M4) as an alias of the J413
