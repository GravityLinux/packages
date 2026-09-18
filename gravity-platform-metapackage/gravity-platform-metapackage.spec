# This package does not have anything to compile and have debug symbols
%global debug_package %{nil}

Name:           gravity-platform-metapackage
Vendor:         Gravity Linux
Version:        0
Release:        102.gravity%{?dist}
Summary:        Metapackage declaring Asahi platform dependencies
Group:          Metapackages
License:        MIT
URL:            https://pagure.io/fedora-asahi/gravity-platform-metapackage
ExclusiveArch:  aarch64
Source1:        FAR_grub2_config_fixup.sh
Source2:        10-asahi-browser-apple.conf

BuildRequires:  systemd-rpm-macros
Requires:       %{name}-core = %{version}-%{release}
Requires:       gravity-repos
Requires:       gravity-remix-scripts
Requires:       gravity-release
Requires:       gravity-appstream-metadata
Requires:       gravity-logos
Requires:       (%{name}-audio = %{version}-%{release} if pipewire)
Requires:       (%{name}-plasma = %{version}-%{release} if plasma-desktop)
Requires:       (%{name}-fex = %{version}-%{release} if fex-emu)
Requires:       (%{name}-mesa = %{version}-%{release} if mesa-dri-drivers)
%dnl If/when we have desktop subpackages or whatever, we can make them
%dnl conditional dependencies with the following format:
%dnl Requires:       (%{name}-desktop-<variant> = %{version}-%{release} if <desktop-main-package>)
Requires:       (%{name}-desktop = %{version}-%{release} if fedora-release-kde)
Requires:       (%{name}-desktop = %{version}-%{release} if fedora-release-workstation)

%description
This is a simple RPM package that defines the Asahi platform
software dependencies.

%files
%{_sysconfdir}/dnf/protected.d/%{name}.conf

%dnl -------------------------------------------------------------------

%package core
Summary:        Metapackage declaring core Asahi platform dependencies
Requires:       alsa-ucm-asahi
Requires:       gravity-fwupdate >= 20260915-100
Requires:       dracut-gravity >= 20260915-100
Requires:       kernel-16k
Requires:       kernel-16k-modules-extra
Requires:       update-m1n1
Requires:       tiny-dfr
Requires:       (widevine-installer if (chromium or firefox))
%if 0%{?fedora} >= 43
%dnl Require the dnf5 backend for PackageKit
Requires:       (PackageKit-backend-dnf5%{?_isa} if PackageKit%{?_isa})
%endif
%dnl Block the 4k kernel
Conflicts:      kernel-core
Conflicts:      kernel-devel
Conflicts:      kernel-debug-core
Conflicts:      kernel-debug-devel
%dnl Block the 64k kernel
Conflicts:      kernel-64k-core
Conflicts:      kernel-64k-devel
Conflicts:      kernel-64k-debug-core
Conflicts:      kernel-64k-debug-devel
%dnl drop firefox subpackage as the arch override in the UA is no longer needed
Obsoletes:      %{name}-firefox < 22
%dnl obsolete all mesa-asahi-*-flatpak packages
Obsoletes:      mesa-asahi-22.08-flatpak < 25.0
Obsoletes:      mesa-asahi-23.08-flatpak < 25.2
Obsoletes:      mesa-asahi-24.08-flatpak < 25.2
%dnl nothing should depend on these but add provides anyway
Provides:       mesa-asahi-22.08-flatpak
Provides:       mesa-asahi-23.08-flatpak
Provides:       mesa-asahi-24.08-flatpak
Obsoletes:      gravity-platform-metapackage-flatpak < 24
Provides:       gravity-platform-metapackage-flatpak

%description core
This package declares the core dependencies for the Asahi platform.

%files core
%dnl No files to ship

# cleanup orphaned grub2 modules in /boot/grub2/arm64-efi mistakenly installed
# kiwi.
# Check if ext2.mod in /boot/grub2/arm64-efi is newer than the system module.
# This means most likely `grub2-install` was used.
%if 0%{?fedora} && 0%{?fedora} <= 42
%posttrans core
if [ -d /boot/grub2/arm64-efi ]; then
    if [ ! -d /usr/lib/grub/arm64-efi ]; then
        echo "Cleaning stale grub2 modules in /boot/grub2/arm64-efi"
        rm -rf /boot/grub2/arm64-efi
    elif [ ! /boot/grub2/arm64-efi/ext2.mod -nt /usr/lib/grub/arm64-efi/ext2.mod ]; then
        echo "Cleaning stale grub2 modules in /boot/grub2/arm64-efi"
        rm -rf /boot/grub2/arm64-efi
    fi
fi
%endif

%dnl -------------------------------------------------------------------

%package audio
Summary:        Metapackage declaring audio support Asahi platform dependencies
Requires:       asahi-audio >= 0.5-1
# J773g speaker protection is implemented by the kernel driver.
Conflicts:      pulseaudio

%description audio
This package declares the audio dependencies for the Asahi platform.

%files audio
%dnl No files to ship

%dnl -------------------------------------------------------------------

%package plasma
Summary:        Metapackage declaring Plasma desktop support Asahi platform dependencies
%dnl No deps at this time, just a temporary KWin workaround

%description plasma
This package declares the KDE Plasma dependencies for the Asahi platform.

%files plasma
%{_sysconfdir}/xdg/kcminputrc


%dnl -------------------------------------------------------------------

%package fex
Summary:        Metapackage declaring muvm support Asahi platform dependencies
Requires:       muvm
Requires:       fex-emu-rootfs-fedora
%if 0%{?fedora} && 0%{?fedora} >= 43
Obsoletes:      mesa-fex-emu-overlay-i386 < 26.2
Obsoletes:      mesa-fex-emu-overlay-x86_64 < 26.2
%endif
%if 0%{?fedora} && 0%{?fedora} <= 42
Requires:       mesa-fex-emu-overlay-i386
Requires:       mesa-fex-emu-overlay-x86_64
%endif
Requires:       virglrenderer >= 1.2.0

%description fex
This package declares the fex-emu dependencies for the Asahi platform. These allow running
i686/x86_64 applications within a muvm VM, and enable GPU acceleration support using the
appropriate fex-emu rootfs and virglrenderer.

%files fex
%dnl No files to ship

%dnl -------------------------------------------------------------------

%package desktop
Summary:        Metapackage declaring package recommendations for Asahi desktop systems
Requires:       sed
Requires:       grub2-tools-minimal
Requires:       grub2-tools
Recommends:     gravity-battery
Recommends:     mesa-libOpenCL

%description desktop
This package declares recommeded packages for Desktop Environment Asahi platform installations.
This contains the OpenCL runtime and persistant battery charge control support using systemd.

%triggerun desktop -- gravity-release-common < 44
# When upgrading to Fedora 44, mark the system as configured if /etc/reconfigSys doesn't exist
if [ ! -f "%{_sysconfdir}/reconfigSys" ]; then
   touch %{_sysconfdir}/plasma-setup-done
fi
exit 0

%files desktop
%if (0%{?fedora} && 0%{?fedora} < 42)
%{_environmentdir}/50-asahi-gtk-ngl.conf
%endif

%if 0%{?fedora} && 0%{?fedora} <= 42
%{_libexecdir}/%{name}-desktop/

# Adjust grub2 config to Fedora desktop defaults
%dnl %posttrans desktop
%{_libexecdir}/%{name}-desktop/FAR_grub2_config_fixup.sh
%endif

%dnl -------------------------------------------------------------------

%package mesa
Summary:        Metapackage shipping mesa driconf for Asahi systems
Requires:       mesa-filesystem

%description mesa
This package contains asahi specific mesa driconf files

%files mesa
%{_datadir}/drirc.d/10-asahi-browser-apple.conf


%dnl -------------------------------------------------------------------

%prep
%dnl Nothing to do

%build
%dnl Nothing to do

%install
# Install DNF protected package snippet to prevent it from being accidentally uninstalled
mkdir -p %{buildroot}%{_sysconfdir}/dnf/protected.d
echo "%{name}" > %{buildroot}%{_sysconfdir}/dnf/protected.d/%{name}.conf

# Workaround for gtk4 bug:
# https://gitlab.gnome.org/GNOME/gtk/-/issues/7229
# fixed in gtk4 4.18 available in Fedora 42
%if (0%{?fedora} && 0%{?fedora} < 42)
mkdir -p %{buildroot}%{_environmentdir}
echo 'GSK_RENDERER=ngl' > %{buildroot}%{_environmentdir}/50-asahi-gtk-ngl.conf
%endif

# Disable Tap-to-Click by default since it's the less confusing default (force click is always enabled)
mkdir -p %{buildroot}%{_sysconfdir}/xdg
cat > %{buildroot}%{_sysconfdir}/xdg/kcminputrc <<EOF
[Libinput][Defaults]
TapToClick=false
EOF

# Install desktop grub2 config fixup script
%if 0%{?fedora} && 0%{?fedora} <= 42
install -Dpm0755 -t %{buildroot}%{_libexecdir}/%{name}-desktop %SOURCE1
%endif

install -Dpm0644 -t %{buildroot}%{_datadir}/drirc.d %SOURCE2

%changelog
* Fri Sep 18 2026 Gravity Linux maintainers - 0-102.gravity
- Drop userspace speaker protection requirements; J773g protection is in-kernel

* Wed Sep 16 2026 Gravity Linux maintainers - 0-101.gravity
- Require Gravity's downstream speaker protection implementation for audio

* Fri Mar 27 2026 Neal Gompa <ngompa@fedoraproject.org> - 0-29
- Add trigger scriptlet to disable plasma-setup for upgrades to F44

* Sat Jan 10 2026 Neal Gompa <ngompa@fedoraproject.org> - 0-28
- Require the DNF5 backend if PackageKit is installed for F43+

* Mon Dec 08 2025 Janne Grunau <janne-fdr@jannau.net> - 0-27
- Add mesa driconf to override renderer string for web browsers

* Sun Nov 23 2025 Janne Grunau <janne-fdr@jannau.net> - 0-26
- Obsolete mesa overlays on F43 and later

* Sat Nov 08 2025 Janne Grunau <janne-fdr@jannau.net> - 0-25
- Drop flatpak package and obolete all mesa-asahi-*-flatpak
- fex: depend virglrenderer-1.2.0 and drop mesa overlays from F43+
- Execute grub2 config fixup script for desktop installations

* Wed Jul 23 2025 Janne Grunau <janne-fdr@jannau.net> - 0-24
- Drop mesa-asahi-*-flatpak for Fedora 43
- Drop mesa-asahi-24.08-flatpak as the 24.08 FDO runtime ships mesa-25.1

* Mon Apr 28 2025 Janne Grunau <janne-fdr@jannau.net> - 0-23
- Add script to adjust grub2 config to Fedora Desktop defaults
- Cleanup orphaned grub2 efi modules (rhbz#2361849)

* Fri Apr 11 2025 Janne Grunau <janne-fdr@jannau.net> - 0-22
- Drop outdated firefox user-agent override
- Obsolete flatpak mesa extension for EOL 22.08 fdo runtime

* Fri Mar 28 2025 Janne Grunau <janne-fdr@jannau.net> - 0-21
- Remove gtk4 ngl workaround on Fedora 42, bugs are fixed in gtk4 4.18

* Wed Feb 26 2025 Davide Cavalca <dcavalca@fedoraproejct.org> - 0-20
- Use a versioned requirement for gravity-fwupdate to avoid dependency hell
- Add missing changelog entry

* Wed Feb 12 2025 Janne Grunau <janne-fdr@jannau.net> - 0-19
- Replace asahi-fwextract with gravity-fwupdate

* Wed Jan 01 2025 Janne Grunau <janne-fdr@jannau.net> - 0-18
- Use ngl gtk renderer as temporary bug workaround

* Wed Dec 11 2024 Asahi Lina <lina@asahilina.net> - 0-17
- Add fex subpackage for muvm+fex dependencies

* Sun Dec 08 2024 Janne Grunau <janne-fdr@jannau.net> - 0-16
- Remove kwin software cursor workaround

* Mon Dec 02 2024 Janne Grunau <janne-fdr@jannau.net> - 0-15
- Add desktop sub-package for OpenCL/battery charge control

* Wed Sep 25 2024 Janne Grunau <janne-fdr@jannau.net> - 0-14
- Pull mesa-asahi-24.08-flatpak in

* Fri Aug 23 2024 Hector Martin <marcan@fedoraproject.org> - 0-13
- Add kcminputrc snippet to disable Tap-to-Click by default

* Tue Jul 16 2024 Janne Grunau <janne-fdr@jannau.net> - 0-12
- Add flatpak subpackage with GPU/GL extensions for FDO runtimes

* Thu May 30 2024 Davide Cavalca <dcavalca@fedoraproject.org>
- Require the latest dracut-gravity

* Sat Apr 20 2024 Davide Cavalca <dcavalca@fedoraproject.org>
- Rebuild for Fedora Linux 40

* Sun Dec 17 2023 Hector Martin <marcan@fedoraproject.org>
- Make widevine-installer Requires instead of Recommends

* Tue Dec 12 2023 Hector Martin <marcan@fedoraproject.org>
- Add firefox subpackage with UA hack to work around evil websites

* Mon Dec 11 2023 Davide Cavalca <dcavalca@fedoraproject.org>
- Pull in widevine-installer if we have a supported browser

* Mon Nov 27 2023 Hector Martin <marcan@fedoraproject.org>
- Add plasma subpackage with KWin bug workaround

* Thu Nov 09 2023 Hector Martin <marcan@fedoraproject.org>
- Add audio subpackage

* Tue Nov 07 2023 Neal Gompa <ngompa@fedoraproject.org>
- Add protected packages configuration for DNF for this package

* Fri Nov 03 2023 Neal Gompa <ngompa@fedoraproject.org>
- Block 4k and 64k kernel-debug variants

* Wed Oct 04 2023 Neal Gompa <ngompa@fedoraproject.org>
- Block 4k and 64k kernel-devel variants

* Sat Sep 23 2023 Neal Gompa <ngompa@fedoraproject.org>
- Initial package
