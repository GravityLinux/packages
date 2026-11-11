Name:           steam
Version:        1.0.0.85
Release:        13.gravity%{?dist}
Summary:        Launcher for Valve's native ARM64 Steam client
# Only the launcher is packaged. Valve's client is proprietary; each user's
# first start downloads it from Valve (README.md).
License:        MIT
URL:            https://github.com/GravityLinux/packages
Source0:        LICENSE
Source1:        LICENSE.icon
Source2:        README.md
Source10:       steam
Source11:       steam-launch
Source12:       exec-pages.c
Source13:       fetch-client
Source14:       steam.desktop
Source15:       steam.svg
Source20:       first_run.py
Source21:       seed-compat
Source22:       first-run-policy.json
Source30:       test_fetch_client.py
Source31:       test_first_run.py
ExclusiveArch:  aarch64

BuildRequires:  desktop-file-utils
BuildRequires:  gcc
BuildRequires:  python3
BuildRequires:  tar
BuildRequires:  zstd

Requires:       bash, coreutils, tar, zstd, procps-ng, util-linux
Requires:       hicolor-icon-theme
# fetch-client: the first start's download, with zenity's progress window.
Requires:       python3
Requires:       zenity
# Host libraries that the client's ARM64 programs link, plus gtk3 and
# libXScrnSaver, which its browser and user interface load at run time.
Requires:       alsa-lib, atk, at-spi2-atk, at-spi2-core, cairo, cups-libs
Requires:       dbus-libs, expat, fontconfig, freetype, gdk-pixbuf2, gtk2, gtk3
Requires:       ibus-libs, libasyncns, libdrm, libglvnd-egl, libglvnd-glx, libICE
Requires:       libSM, libsndfile, libssh2, libva, libvdpau, libX11, libX11-xcb
Requires:       libxcb, libXcomposite, libXdamage, libXext, libXfixes, libXi
Requires:       libXinerama, libxkbcommon, libXrandr, libXrender, libXScrnSaver
Requires:       libXtst, mesa-libgbm, NetworkManager-libnm, nspr, nss, nss-util
Requires:       openal-soft, pango, pipewire-libs, pulseaudio-libs, sdl2-compat
Requires:       vulkan-loader
# Valve's ARM64 client runs as a 4K process, which needs a P3S kernel; on a
# 16K kernel without P3S it crashes at launch. Requiring the capability makes
# a plain "dnf install steam" on an older install bring the kernel along;
# steam-launch explains the restart until it runs.
Requires:       kernel(p3s)
# The stack it was tested with: the platform metapackage that brings the M4
# boot chain, and the Apple GPU Mesa (its subpackages are pinned to each other).
Requires:       gravity-platform-metapackage-core >= 0-106
Requires:       mesa-dri-drivers >= 26.3.0~devel-105
Requires:       mesa-vulkan-drivers >= 26.3.0~devel-105
# x86 Linux games use Valve's FEX tool, whose graphics driver is this x86
# build of the system Mesa.
Requires:       fex-guestos-mesa
# Windows games: the ARM64 Proton, as the default tool (weak, so either can
# be left out).
Recommends:     proton-gravity-arm64
Recommends:     steam-gravity-proton-default

%description
The steam command, desktop entry and steam:// handler for Valve's native
ARM64 Steam client. The client itself is not part of this package: the first
start downloads it from Valve (about 700 MB) into the user's data directory,
shows the progress, and checks the download before installing it. After that
the client keeps itself up to date.

%package -n steam-gravity-proton-default
Summary:        Make the ARM64 Proton the default Steam compatibility tool
Requires:       steam = %{version}-%{release}
Requires:       proton-gravity-arm64
Requires:       python3

%description -n steam-gravity-proton-default
Makes Proton (ARM64, Gravity) the default compatibility tool. The steam
launcher sets it while Steam is stopped; it only adds the default when none
is set, and keeps existing global and per-game choices.

%prep
%setup -c -T
cp -p %{sources} .

%build
%{__cc} %{build_cflags} -Wall -Wextra -Werror %{build_ldflags} -o exec-pages exec-pages.c

%install
install -Dm755 steam %{buildroot}%{_bindir}/steam
install -Dm755 -t %{buildroot}%{_libexecdir}/steam-gravity exec-pages steam-launch fetch-client seed-compat
install -m644 first_run.py %{buildroot}%{_libexecdir}/steam-gravity/first_run.py
install -Dm644 first-run-policy.json %{buildroot}%{_datadir}/steam-gravity/first-run-policy.json
install -Dm644 steam.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/steam.svg
desktop-file-install --dir=%{buildroot}%{_datadir}/applications steam.desktop

%check
python3 test_fetch_client.py
python3 test_first_run.py

%files
%license LICENSE LICENSE.icon
%doc README.md
%{_bindir}/steam
%dir %{_libexecdir}/steam-gravity
%{_libexecdir}/steam-gravity/exec-pages
%{_libexecdir}/steam-gravity/steam-launch
%{_libexecdir}/steam-gravity/fetch-client
%{_datadir}/applications/steam.desktop
%{_datadir}/icons/hicolor/scalable/apps/steam.svg

%files -n steam-gravity-proton-default
%license LICENSE
%dir %{_datadir}/steam-gravity
%{_datadir}/steam-gravity/first-run-policy.json
%{_libexecdir}/steam-gravity/first_run.py
%{_libexecdir}/steam-gravity/seed-compat

%changelog
* Tue Nov 10 2026 Niklas Sheth <hi@niklassheth.com> - 1.0.0.85-13.gravity
- The Steam client is no longer part of the package. The first start
  downloads it from Valve (about 700 MB), shows the progress, checks the
  download and continues an interrupted one. A client that is already
  installed stays as it is.
- Install the graphics driver for x86 Linux games (fex-guestos-mesa) with
  Steam.
