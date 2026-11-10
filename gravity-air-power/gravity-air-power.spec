Name:           gravity-air-power
Vendor:         Gravity Linux
Version:        20261104
Release:        2.gravity%{?dist}
Summary:        Sleep and power defaults for the M4 MacBook Air (J713)
License:        MIT
URL:            https://github.com/GravityLinux
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  make
BuildRequires:  python3
BuildRequires:  systemd-rpm-macros
Requires:       python3
Requires:       systemd
Requires:       systemd-udev
# Every unit checks the board (apple,j713), so other machines are unaffected.
Supplements:    gravity-platform-metapackage-core

%description
Power defaults for the M4 MacBook Air (J713), inactive on other machines:
- suspend-to-idle on lid close, overriding Gravity's no-sleep policy for
  the boot when the running kernel supports s2idle (gravity.air_s2idle=0
  keeps the no-sleep policy);
- a logind sleep block while a USB4/Thunderbolt link is up, since the
  kernel refuses to suspend then, and a re-check of the closed lid after
  the link goes away;
- cpufreq boost off by default on the fanless Air;
- Wi-Fi power saving (brcmfmac PM_MAX) while the lid is closed.

%prep
%autosetup

%build

%check
%make_build check

%install
%make_install PREFIX=%{_prefix} LIBEXECDIR=%{_libexecdir} UNITDIR=%{_unitdir} \
    UDEVRULESDIR=%{_udevrulesdir} NMDISPATCHERDIR=%{_prefix}/lib/NetworkManager/dispatcher.d

# systemd's and udev's file triggers reload the managers. The units take
# effect from the next boot; the USB4 rule applies to the next link.

%files
%license LICENSE
%doc README.md
%{_libexecdir}/gravity-air-s2idle-default
%{_libexecdir}/gravity-air-cpufreq-default
%{_libexecdir}/gravity-lid-wifi
%{_libexecdir}/gravity-usb4-sleep-release
%{_unitdir}/gravity-air-s2idle-default.service
%{_unitdir}/gravity-air-cpufreq-default.service
%{_unitdir}/gravity-lid-wifi.service
%{_unitdir}/gravity-usb4-sleep-inhibit@.service
%{_unitdir}/sysinit.target.wants/gravity-air-s2idle-default.service
%{_unitdir}/sysinit.target.wants/gravity-air-cpufreq-default.service
%{_udevrulesdir}/90-gravity-lid-wifi.rules
%{_udevrulesdir}/90-gravity-usb4-sleep-inhibit.rules
%{_prefix}/lib/NetworkManager/dispatcher.d/90-gravity-lid-wifi

%changelog
* Wed Nov 04 2026 Gravity Linux maintainers - 20261104-2.gravity
- gravity-usb4-sleep-release: query PowerDevil on the user's session bus
  socket as that user instead of busctl --machine=USER@ (a systemd-run
  transient unit and PAM login session per call), which failed when a USB4
  SSD was unplugged with the lid closed and left the Air awake
- Log busctl's error output when a D-Bus call fails

* Wed Nov 04 2026 Gravity Linux maintainers - 20261104-1.gravity
- Package the J713 Air sleep policy, previously installed by hand from
  m4-linux/lid-wifi-standby: s2idle is selected by the board compatible
  instead of the gravity.air_s2idle=1 lab argument (=0 disables it), and
  the research retention parameters are no longer checked
- Hold a logind sleep block while a USB4 domain exists: lid close no longer
  retries suspend every ~10 s (with a Wi-Fi reconnect each time) while the
  ACIO refuses to sleep; re-check the closed lid when the link goes away
