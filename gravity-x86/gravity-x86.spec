Name:           gravity-x86
Version:        0.3.0
Release:        2.gravity%{?dist}
Summary:        Run x86 programs through FEX with 4K pages on P3S kernels
License:        MIT
URL:            https://github.com/GravityLinux
Source0:        %{name}-%{version}.tar.gz
ExclusiveArch:  aarch64

BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  systemd-rpm-macros
Requires:       binfmt-dispatcher
Requires:       fex-emu
# fex-4k execs these paths directly. (The rootfs image the service mounts,
# /usr/share/fex-emu/RootFS/default.erofs, stays a package dependency: dnf
# does not load file lists by default, so a /usr/share file dependency would
# not resolve.)
Requires:       /usr/bin/FEXInterpreter
Requires:       /usr/bin/binfmt-dispatcher
Requires:       fex-emu-rootfs-fedora
Requires:       erofs-fuse
# The root filesystem's Mesa layer (gravity-x86-rootfs.service).
Requires:       gravity-x86-mesa
# Only where Gravity's FEX platform set meets a P3S kernel package (which must
# provide kernel(p3s)); other installs keep binfmt-dispatcher's muvm path alone.
Supplements:    (gravity-platform-metapackage-fex and kernel(p3s))
# Replaces the earlier runtime with its own rootfs, server unit and Steam
# launcher; native ARM64 Steam is packaged separately.
# Renamed from p3s-fex-4k (never published; test installs upgrade cleanly).
Obsoletes:      p3s-fex-4k < %{version}-%{release}
Provides:       p3s-fex-4k = %{version}-%{release}
Obsoletes:      m4-native-gaming < 0.2
Obsoletes:      m4-native-gaming-mesa-x86 < 27

%description
Runs x86 programs through FEX with 4K pages on ARM64 kernels with per-process
4K pages (P3S), instead of in a muvm virtual machine, and points FEX at the
packaged Fedora x86 root filesystem, with the Apple GPU Mesa from
gravity-x86-mesa mounted over it. On kernels without P3S, x86 programs go
to binfmt-dispatcher as before.

%prep
%autosetup

%build
%make_build CC="%{__cc}" CFLAGS="%{build_cflags}" LDFLAGS="%{build_ldflags}"

%install
%make_install PREFIX=%{_prefix} LIBEXECDIR=%{_libexecdir} BINFMTDIR=%{_binfmtdir} DATADIR=%{_datadir} \
    UNITDIR=%{_unitdir}

# systemd's binfmt.d file trigger registers and removes the rules.

%preun
%systemd_preun gravity-x86-rootfs.service

%postun
%systemd_postun_with_restart gravity-x86-rootfs.service

%posttrans
# An install renamed from p3s-fex-4k may keep that package's Config.json
# (%%config(noreplace)), which names the old mount point.
if grep -qx '{"Config": {"RootFS": "/run/p3s-fex-4k/rootfs"}}' %{_datadir}/fex-emu/Config.json 2>/dev/null; then
    sed -i 's|/run/p3s-fex-4k/rootfs|/run/gravity-x86/rootfs|' %{_datadir}/fex-emu/Config.json
fi
# FEX's configuration names the mounted root filesystem from now on.
if [ -d /run/systemd/system ]; then
    systemctl daemon-reload || :
    systemctl start gravity-x86-rootfs.service || :
fi

%triggerin -- fex-emu-rootfs-fedora
systemctl try-restart gravity-x86-rootfs.service >/dev/null 2>&1 || :

%files
%license LICENSE
%doc README.md
%{_libexecdir}/gravity-x86/
%{_binfmtdir}/zzz-gravity-x86-x86.conf
%{_binfmtdir}/zzz-gravity-x86-x86_64.conf
%{_unitdir}/gravity-x86-rootfs.service
%{_unitdir}/multi-user.target.wants/gravity-x86-rootfs.service
%config(noreplace) %{_datadir}/fex-emu/Config.json

%changelog
* Sun Nov 08 2026 Niklas Sheth <niklassheth@gmail.com> - 0.3.0-2.gravity
- Supplement the kernel(p3s) capability instead of the kernel-p3s name.
- Require /usr/bin/FEXInterpreter and /usr/bin/binfmt-dispatcher, which
  fex-4k execs.

* Sun Nov 08 2026 Niklas Sheth <niklassheth@gmail.com> - 0.3.0-1.gravity
- Rename p3s-fex-4k to gravity-x86 (service gravity-x86-rootfs.service, binfmt
  rules zzz-gravity-x86-*.conf, /usr/libexec/gravity-x86, /run/gravity-x86,
  Mesa layer gravity-x86-mesa in /usr/share/gravity-x86); obsoletes and
  provides p3s-fex-4k.

* Mon Nov 02 2026 M4 Native Gaming contributors - 0.3.0-1
- Mount the Fedora rootfs image with p3s-fex-4k-mesa's x86 Mesa over it at
  boot and point FEX at the result, so x86 GL and Vulkan programs use the
  Apple GPU: the image's Fedora Mesa cannot submit work to it.

* Sun Nov 01 2026 M4 Native Gaming contributors - 0.2.0-2
- Terminate the re-exec argument vector: an argument after the program
  (e.g. glxinfo -B) fell back to binfmt-dispatcher and muvm.

* Sun Nov 01 2026 M4 Native Gaming contributors - 0.2.0-1
- Split from m4-native-gaming 0.1.9: keep only x86 programs in 4K mode.
  A small handler requests 4K pages and starts stock FEXInterpreter, which
  runs its own server and mounts the packaged erofs rootfs.
- Drop the prepared overlay rootfs, per-user server unit, binfmt registry
  transaction, Vulkan thunk settings, x86 Mesa overlay and the Steam launcher.
