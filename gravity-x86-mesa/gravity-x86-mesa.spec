# Repacks the two x86 trees of the mesa-fex-guest RPM that COPR built on
# x86_64 from the system Mesa's pinned source (see mesa-fex-guest.spec), as
# noarch packages for ARM64 systems. Nothing is compiled here.
#
# tools/package.py defines from sources.json and downloads.lock.json:
# gravity_rpm_url (the pinned COPR result, checked against its SHA256),
# gravity_rpm_version and gravity_rpm_release (that RPM's, which this package
# mirrors) and gravity_git_ref (the Mesa commit it was built from). `make pin`
# updates them after COPR builds mesa-fex-guest; nothing here changes on a
# Mesa update.
#
# The x86 ELF files must not feed RPM's dependency generators, stripping or
# build-id links.
%global debug_package %{nil}
%global __os_install_post %{nil}
%global _build_id_links none
%global _binaries_in_noarch_packages_terminate_build 0
%global mesa_rev %{lua:print(string.sub(rpm.expand("%{gravity_git_ref}"), 1, 10))}
%global payload payload/usr/lib/mesa-fex-guest

Name:           gravity-x86-mesa
Version:        %{gravity_rpm_version}
Release:        %{gravity_rpm_release}%{?dist}
Summary:        Apple GPU x86 Mesa for gravity-x86's FEX root filesystem
License:        MIT
URL:            https://github.com/GravityLinux/mesa
Source0:        %{gravity_rpm_url}
Source1:        README.md
Source2:        README-fex-guestos-mesa.md
BuildArch:      noarch
BuildRequires:  cpio
AutoReqProv:    no
# x86 builds of exactly the system Mesa's revision: mesa-dri-drivers provides
# it (first 10 hex digits of the pinned commit).
Requires:       gravity-mesa-revision = %{mesa_rev}
# Renamed from p3s-fex-4k-mesa (never published). Its versions
# (26.3.0~YYYYMMDDgitHASH) sort above 26.3.0~devel, so obsolete by name.
Obsoletes:      p3s-fex-4k-mesa < 27
Provides:       p3s-fex-4k-mesa = %{version}-%{release}

%description
x86_64 and i686 builds of the Mesa revision that the system runs (GL with the
asahi and zink drivers, Vulkan with Honeykrisp), in Fedora's lib64/lib layout.
gravity-x86 mounts them over the packaged Fedora x86 root filesystem, so x86
programs run through FEX use the Apple GPU instead of the root filesystem's
Fedora Mesa, which cannot submit work to it.

%package -n fex-guestos-mesa
Summary:        x86 graphics provider for Steam's FEX compatibility tool
# Mesa is MIT; the rest are the licenses of the Fedora packages it contains
# (texts in usr/share/licenses, versions in MANIFEST.json).
License:        MIT AND LGPL-2.1-or-later AND GPL-3.0-or-later WITH GCC-exception-3.1 AND GPL-3.0-or-later AND GPL-2.0-only AND Apache-2.0 AND BSD-3-Clause AND Zlib
AutoReqProv:    no
Requires:       gravity-mesa-revision = %{mesa_rev}
# Native ARM64 Steam runs native Linux x86 games through Valve's FEX tool,
# which needs this tree.
Supplements:    steam

%description -n fex-guestos-mesa
The x86_64 and i386 system tree that Valve's FEX compatibility tool for
ARM64 Steam uses at /usr/share/guestos/fex-mesa: its FEX root filesystem and
the pressure-vessel graphics provider (graphics_provider.json) for native
Linux x86 games. It holds Fedora's x86 glibc, C++ runtime, X11, Wayland and
libglvnd libraries, a shell for the runtime's entry point, and x86 builds of
the Apple GPU Mesa revision that the system runs, in Arch-style lib/lib32
directories.

%prep
rm -rf payload
mkdir payload
rpm2cpio %{SOURCE0} | cpio -idm --quiet --no-absolute-filenames -D payload
for tree in gravity-x86 guestos; do
  grep -q '"mesa_revision": "%{gravity_git_ref}"' %{payload}/MANIFEST-$tree.json \
    || { echo "$tree: not built from %{gravity_git_ref}" >&2; exit 1; }
done

%build

%install
mkdir -p %{buildroot}%{_datadir}/gravity-x86/mesa-x86 %{buildroot}%{_datadir}/guestos/fex-mesa
cp -a %{payload}/gravity-x86/. %{buildroot}%{_datadir}/gravity-x86/mesa-x86/
cp -a %{payload}/guestos/. %{buildroot}%{_datadir}/guestos/fex-mesa/
install -Dm644 %{payload}/MANIFEST-gravity-x86.json %{buildroot}%{_docdir}/%{name}/MANIFEST.json
install -Dm644 %{SOURCE1} %{buildroot}%{_docdir}/%{name}/README.md
install -Dm644 %{payload}/MANIFEST-guestos.json %{buildroot}%{_docdir}/fex-guestos-mesa/MANIFEST.json
install -Dm644 %{SOURCE2} %{buildroot}%{_docdir}/fex-guestos-mesa/README.md

%posttrans
# Remount so that new x86 programs see this Mesa; running ones keep theirs.
systemctl try-restart gravity-x86-rootfs.service >/dev/null 2>&1 || :

%files
%dir %{_datadir}/gravity-x86
%{_datadir}/gravity-x86/mesa-x86/
%doc %{_docdir}/%{name}/MANIFEST.json
%doc %{_docdir}/%{name}/README.md

%files -n fex-guestos-mesa
%dir %{_datadir}/guestos
%{_datadir}/guestos/fex-mesa/
%doc %{_docdir}/fex-guestos-mesa/MANIFEST.json
%doc %{_docdir}/fex-guestos-mesa/README.md

%changelog
* Tue Nov 10 2026 Niklas Sheth <hi@niklassheth.com>
- Build from source: repack the trees of mesa-fex-guest, which COPR builds
  on x86_64 from the system Mesa's pinned source and Fedora's x86 packages,
  instead of carrying prebuilt payloads. fex-guestos-mesa becomes a
  subpackage of this source package. Version and Release follow the
  mesa-fex-guest build, so they move with each Mesa update.
