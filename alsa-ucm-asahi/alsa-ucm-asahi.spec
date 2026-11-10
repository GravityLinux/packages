%global srcname alsa-ucm-conf-asahi

Name:           alsa-ucm-asahi
Version:        10
Release:        102.gravity%{?dist}
Vendor:         Gravity Linux
Summary:        ALSA Use Case Manager configuration (and topologies) for Apple silicon devices
License:        BSD-3-Clause

URL:            https://github.com/AsahiLinux/alsa-ucm-conf-asahi
Source:         %{url}/archive/v%{version}/%{srcname}-%{version}.tar.gz
# Gravity: J713 (MacBook Air 13", M4) speakers and headphones
Patch:          0001-macaudio-add-the-J713.patch
# Gravity: J713 headphones back on the J413 DAC mapping (speculative, pending a listen test)
Patch:          0002-macaudio-J713-headphones-use-the-J413-DAC-mapping.patch
# Gravity: J713 internal mics (AOP card AppleJ713HPAI)
Patch:          0003-aop_audio-add-the-J713-MacBook-Air-13-M4-mics.patch

BuildArch:      noarch

Requires:       alsa-ucm >= 1.2.7.2
Provides:       gravity-alsa-ucm-asahi = %{version}-%{release}

%description
The ALSA Use Case Manager configuration (and topologies) for Apple silicon devices.

%prep
%autosetup -n %{srcname}-%{version} -p1

%install
install -dm 755 %{buildroot}%{_datadir}/alsa/ucm2/conf.d/
cp -a ucm2/conf.d/aop_audio/ %{buildroot}%{_datadir}/alsa/ucm2/conf.d/
cp -a ucm2/conf.d/macaudio/ %{buildroot}%{_datadir}/alsa/ucm2/conf.d/

%files
%license LICENSE.asahi
%doc README.asahi
%{_datadir}/alsa/ucm2/conf.d/aop_audio/
%{_datadir}/alsa/ucm2/conf.d/macaudio/

%changelog
* Sun Nov 08 2026 Niklas Sheth <niklassheth@gmail.com> - 10-102.gravity
- J713 headphones: back to the J413/J613 DAC mapping (speculative; the earlier
  by-ear swap was most likely the T8132 TDM slot-alignment bug, since fixed)
- Add the J713 internal mics (AOP)

* Sun Nov 08 2026 Niklas Sheth <niklassheth@gmail.com> - 10-100.gravity
- Rebase on Fedora's alsa-ucm-asahi 10 package
- Add the J713 (MacBook Air 13", M4) speakers and headphones
