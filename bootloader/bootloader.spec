%global debug_package %{nil}
# Preserve the upstream binary/config names used by the boot chain.
%global upstream_name m1n1
%global buildflags RELEASE=1 LOGO=gravity

# We need to vendor fatfs because m1n1 stage1 relies on unreleased changes
# (notably, the lfn feature): https://github.com/rafalh/rust-fatfs/issues/81
%global fatfs_commit 4eccb50d011146fbed20e133d33b22f3c27292e7

%global _description %{expand:
m1n1 is the bootloader developed by the Asahi Linux project to bridge the Apple
(XNU) boot ecosystem to the Linux boot ecosystem.}

%global srcversion 1.6.1

Name:           bootloader
Vendor:         Gravity Linux
Version:        %(echo '%{srcversion}' | tr '-' '~')
Release:        103.gravity%{?dist}
Summary:        Bootloader and experimentation playground for Apple Silicon

# The M4 fork adds GPL-2.0-only contributions; vendored projects retain their licenses.
# See the "License" section in README.md for the breakdown
#
# The following breakdown only covers the rust dependencies
# MIT
# MIT OR Apache-2.0
# LICENSE.dependencies contains a full license breakdown of the rust dependencies
License:        GPL-2.0-only AND MIT AND CC0-1.0 AND OFL-1.1-RFN AND Zlib AND (BSD-2-Clause OR GPL-2.0-or-later) AND (BSD-3-Clause OR GPL-2.0-or-later) AND MIT AND (MIT OR Apache-2.0) AND CC-BY-4.0
URL:            https://github.com/GravityLinux/bootloader
Source0:        %{name}-%{srcversion}.tar.gz
Source:         https://github.com/rafalh/rust-fatfs/archive/%{fatfs_commit}/rust-fatfs-%{fatfs_commit}.tar.gz
# * Vendor git dependency rust-fatfs and ensure its dependencies are
#   included as well.
Patch:          m1n1-1.6.1-rust-deps.patch

BuildRequires:  gcc
BuildRequires:  make

# For the bootloader logos and the framebuffer console
BuildRequires:  adobe-source-code-pro-fonts
BuildRequires:  coreutils
BuildRequires:  fontconfig
BuildRequires:  gravity-logos >= 20260915-101.gravity
BuildRequires:  ImageMagick >= 7

# For the udev rule
BuildRequires:  systemd-rpm-macros

# For the rust dependencies
BuildRequires:  cargo-rpm-macros >= 24
BuildRequires:  rust-std-static-aarch64-unknown-none-softfloat

# m1n1 is a bootloader and runs on aarch64 metal, but we declare the package as
# noarch to support remote debugging/development usecases via m1n1-tools
BuildArch:      noarch
# The aarch64-unknown-none-softfloat rust target is only available on aarch64
ExclusiveArch:  aarch64 noarch
# Ensure we obsolete the old arched packages; drop once f45 is EOL
Provides:       m1n1 = %{version}-%{release}
Obsoletes:      m1n1 < %{version}-%{release}

# These are bundled, modified and statically linked into m1n1
Provides:       bundled(arm-trusted-firmware)
Provides:       bundled(dwc3)
Provides:       bundled(dlmalloc)
Provides:       bundled(PDCLib)
Provides:       bundled(libfdt)
Provides:       bundled(minilzlib)
Provides:       bundled(tinf)

%description    %_description

%package        stage1
Provides:       m1n1-stage1 = %{version}-%{release}
Obsoletes:      m1n1-stage1 < %{version}-%{release}
Summary:        %{summary}
# The following breakdown only covers the rust dependencies
# Apache-2.0 OR MIT
# MIT
# MIT OR Apache-2.0
License:        GPL-2.0-only AND MIT AND CC0-1.0 AND OFL-1.1-RFN AND Zlib AND (BSD-2-Clause OR GPL-2.0-or-later) AND (BSD-3-Clause OR GPL-2.0-or-later) AND (Apache-2.0 OR MIT) AND MIT AND (MIT OR Apache-2.0) AND CC-BY-4.0
# LICENSE.dependencies contains a full license breakdown of the rust dependencies

# This is vendored and statically linked into m1n1 when building for stage 1
Provides:       bundled(crate(fatfs))= 0.4.0

%description    stage1 %_description

This package contains the stage1 build of m1n1 that is used by the Gravity Linux
installer.

%package        tools
Provides:       m1n1-tools = %{version}-%{release}
Obsoletes:      m1n1-tools < %{version}-%{release}
Summary:        Developer tools for m1n1
License:        GPL-2.0-only AND MIT
Requires:       %{name} = %{version}-%{release}
Requires:       python3
Requires:       python3dist(construct)
Requires:       python3dist(pyserial)
Requires:       systemd-udev

%description    tools %_description

This package contains various developer tools for m1n1.

%prep
%autosetup -N -n %{name}-%{srcversion}
mkdir -p rust/vendor/rust-fatfs
tar -xf %{SOURCE1} -C rust/vendor/rust-fatfs --strip-components 1
%autopatch -p1
%dnl delete rust/Cargo.lock to avoid the locked versions and drop it from
%dnl RUST_LIB's dependencies as the package build is one shot
/usr/bin/rm -f rust/Cargo.lock
sed -ie 's;\(^build/$(RUST_LIB):.*\) rust/Cargo.lock$;\1;' Makefile

# Use our logos
# Carry attribution with the embedded artwork in both binary packages.
mkdir gravity-artwork-notices
cp %{_datadir}/gravity-logos/{LICENSE,README.md,TRADEMARKS.md} gravity-artwork-notices/
pushd data
ln -s %{_datadir}/pixmaps/bootloader/bootlogo_128.png gravity_128.png
ln -s %{_datadir}/pixmaps/bootloader/bootlogo_256.png gravity_256.png
popd

# Use our fonts
font="$(fc-match "Source Code Pro:bold" 'file' | cut -d= -f2)"
if [ ! -e "$font" ]; then
    echo "Failed to find font"
    exit 1
fi

pushd font
rm SourceCodePro-Bold.ttf font.bin font_retina.bin
./makefont.sh 8 16 12 "$font" font.bin
./makefont.sh 16 32 25 "$font" font_retina.bin
popd

# Generate rust dependencies
%cargo_prep

%generate_buildrequires
cd rust
%cargo_generate_buildrequires -f chainload

%build
%make_build %{buildflags} CHAINLOADING=1
mv build build-stage1
pushd rust
%{cargo_license_summary} -f chainload
%{cargo_license} -f chainload > ../build-stage1/LICENSE.dependencies
popd

%make_build %{buildflags}
pushd rust
%{cargo_license_summary}
%{cargo_license} > ../build/LICENSE.dependencies
popd

%install
install -Dpm0644 -t %{buildroot}%{_libdir}/%{upstream_name} \
  build/%{upstream_name}.{bin,macho} build/%{upstream_name}-asahi.bin
# install backwards compatibility symlink since update-m1n1 hardcodes
# `/usr/lib64/m1n1/m1n1.bin` as m1n1 binary
# check if the dir exists since %{_libdir} expands to "/usr/lib64" for
# aarch64 builds in mock
if [ ! -d %{buildroot}%{_exec_prefix}/lib64/%{upstream_name} ]; then
  mkdir -p %{buildroot}%{_exec_prefix}/lib64/%{upstream_name}
  ln -s %{_libdir}/%{upstream_name}/%{upstream_name}.bin \
    %{buildroot}%{_exec_prefix}/lib64/m1n1/%{upstream_name}.bin
fi
install -Dpm0644 -t %{buildroot}%{_libdir}/%{upstream_name}-stage1 \
  build-stage1/%{upstream_name}.{bin,macho} build-stage1/%{upstream_name}-asahi.bin
install -Ddpm0755 %{buildroot}%{_libexecdir}/%{upstream_name}
cp -pr proxyclient tools %{buildroot}%{_libexecdir}/%{upstream_name}/
install -Dpm0644 -t %{buildroot}%{_udevrulesdir} udev/80-m1n1.rules
install -Dpm0644 m1n1.conf.example %{buildroot}%{_sysconfdir}/m1n1.conf

%files
%license LICENSE.GPL2 LICENSE.MIT 3rdparty_licenses/LICENSE.* build/LICENSE.dependencies
%license gravity-artwork-notices
%doc README.md
%doc m1n1.conf.example
%{_libdir}/%{upstream_name}/
%{_exec_prefix}/lib64/%{upstream_name}
%config(noreplace) %{_sysconfdir}/m1n1.conf

%files stage1
%license LICENSE.GPL2 LICENSE.MIT 3rdparty_licenses/LICENSE.* rust/vendor/rust-fatfs/LICENSE.txt build-stage1/LICENSE.dependencies
%license gravity-artwork-notices
%doc README.md
%{_libdir}/%{upstream_name}-stage1/

%files tools
%{_libexecdir}/%{upstream_name}/
%{_udevrulesdir}/80-m1n1.rules

%changelog
* Tue Sep 15 2026 Gravity Linux maintainers - 1.6.1-102.gravity
- Rename packages to bootloader and use GravityLinux/bootloader sources
- Preserve m1n1 runtime paths and provide compatibility package names

* Tue Sep 15 2026 Gravity Linux maintainers - 1.6.1-101.gravity
- Include CC BY 4.0 artwork licensing and attribution in branded binaries

* Tue Sep 15 2026 Gravity Linux maintainers - 1.6.1-100.gravity
- Build Gravity M4 fork with Gravity boot logos
