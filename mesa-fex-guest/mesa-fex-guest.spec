# x86_64 and i686 builds of the system Mesa's source (sources.json "mesa"),
# assembled into the two x86 trees that FEX uses on ARM64 Gravity systems.
# Built in the fedora-44-x86_64 chroot only: the i686 libraries are built with
# -m32 against Fedora's i686 packages, which the x86_64 repositories carry, so
# one build produces both architectures and the guestos tree's ld.so.cache can
# be checked with its own x86 ldconfig. gravity-x86-mesa (aarch64 chroot)
# repacks this RPM's trees as noarch packages; nothing here is installed on
# ARM64 systems directly.
#
# tools/package.py defines gravity_source_version and gravity_source_release
# from mesa.spec and gravity_git_ref from sources.json, so a Mesa update needs
# no edit here. Bump the number after gravity_source_release for packaging
# changes and for rebuilds that pick up Fedora updates of the guestos
# libraries.
%global debug_package %{nil}
%global _build_id_links none
# The trees keep Fedora's x86 libraries byte for byte: no stripping or other
# post-install processing (the install section strips debug sections from Mesa's own
# files), and no automatic dependencies on files in a private directory.
%global __os_install_post %{nil}
# Like mesa.spec: LTO is known to break some games.
%global _lto_cflags %{nil}
%global treedir %{_prefix}/lib/%{name}
%global rev10 %{lua:print(string.sub(rpm.expand("%{gravity_git_ref}"), 1, 10))}

Name:           mesa-fex-guest
Version:        %{gravity_source_version}
Release:        %{gravity_source_release}.1%{?dist}
%global ver %{gsub %version ~ -}
Summary:        x86 Apple GPU Mesa trees for FEX on ARM64 Gravity systems
# Mesa is MIT; the guestos tree also holds the Fedora packages listed in
# guestos-packages.txt (license texts in its usr/share/licenses).
License:        MIT AND LGPL-2.1-or-later AND GPL-3.0-or-later WITH GCC-exception-3.1 AND GPL-3.0-or-later AND GPL-2.0-only AND Apache-2.0 AND BSD-3-Clause AND Zlib
URL:            https://github.com/GravityLinux/mesa
Source0:        mesa-%{ver}.tar.xz
Source1:        assemble.py
Source2:        guestos-packages.txt
Source3:        README.md
ExclusiveArch:  x86_64
AutoReqProv:    no
# gravity-x86-mesa checks this against sources.json when it is pinned.
Provides:       mesa-fex-guest(git-ref) = %{gravity_git_ref}

# Build-machine tools (mesa_clc, vtn_bindgen2, asahi_clc), as in mesa.spec.
BuildRequires:  meson >= 1.4.0
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  binutils
BuildRequires:  python3
BuildRequires:  python3-mako
BuildRequires:  python3-packaging
BuildRequires:  python3-pycparser
BuildRequires:  python3-pyyaml
BuildRequires:  bison
BuildRequires:  flex
BuildRequires:  glslang
BuildRequires:  vulkan-headers
BuildRequires:  llvm-devel
BuildRequires:  clang-devel
BuildRequires:  pkgconfig(libclc)
BuildRequires:  pkgconfig(LLVMSPIRVLib)
BuildRequires:  pkgconfig(SPIRV-Tools)
BuildRequires:  pkgconfig(wayland-scanner)
BuildRequires:  pkgconfig(wayland-protocols) >= 1.41
BuildRequires:  rpm
# Target libraries, x86_64 and i686.
%global target_devel glibc-devel libstdc++-devel libatomic libdrm-devel expat-devel zlib-ng-compat-devel libzstd-devel wayland-devel libdisplay-info-devel libX11-devel libXext-devel libXdamage-devel libXfixes-devel libXxf86vm-devel libXrandr-devel libXrender-devel libXau-devel libxcb-devel libxshmfence-devel xcb-util-keysyms-devel libglvnd-devel systemd-devel spirv-tools-devel libffi-devel
%{lua:
for pkg in rpm.expand("%{target_devel}"):gmatch("%S+") do
  print("BuildRequires:  " .. pkg .. "(x86-64)\n")
  print("BuildRequires:  " .. pkg .. "(x86-32)\n")
end
}

%description
x86_64 and i686 builds of Gravity's Mesa (GL with the asahi and zink
drivers, Vulkan with Honeykrisp), assembled into two trees below
%{treedir}: the Mesa layer that gravity-x86 mounts over Fedora's x86 root
filesystem, and the x86 system tree that Valve's FEX tool for ARM64 Steam
uses at /usr/share/guestos/fex-mesa. gravity-x86-mesa and fex-guestos-mesa
install them on ARM64 systems; see README.md.

%generate_buildrequires
# The guestos tree's Fedora packages (guestos-packages.txt).
sed 's/#.*//' %{SOURCE2} | while read -r name arches; do
  for arch in $arches; do
    case $arch in
      x86_64) echo "$name(x86-64)" ;;
      i686) echo "$name(x86-32)" ;;
    esac
  done
done

%prep
%autosetup -n mesa-%{ver}
cp %{SOURCE3} .

%build
# Mesa's version string names the pinned commit (as in mesa.spec).
export MESA_GIT_SHA1_OVERRIDE=%{gravity_git_ref}
# The options of the earlier hand-built x86 trees: the Apple GPU drivers and
# zink, no LLVM at run time (so no llvmpipe or lavapipe), precompiled shaders
# from the tools build below.
common=(
  --buildtype=plain --wrap-mode=nodownload -Db_ndebug=true
  --prefix=%{_prefix} --sysconfdir=%{_sysconfdir} --datadir=%{_datadir}
  -Dplatforms=x11,wayland -Dgallium-drivers=asahi,zink -Dvulkan-drivers=asahi
  -Dvulkan-layers= -Dvideo-codecs= -Dtools= -Dbuild-tests=false
  -Dopengl=true -Dgles1=enabled -Dgles2=enabled -Degl=enabled -Dgbm=enabled
  -Dglx=dri -Dglvnd=enabled
  -Dlmsensors=disabled -Dvalgrind=disabled -Dlibunwind=disabled
)

# 1. mesa_clc, vtn_bindgen2 and asahi_clc for the build machine.
CFLAGS="%{build_cflags}" CXXFLAGS="%{build_cxxflags}" LDFLAGS="%{build_ldflags}" \
  meson setup tools "${common[@]}" --libdir=%{_lib} \
  -Dllvm=enabled -Dshared-llvm=enabled -Dmesa-clc=enabled -Dprecomp-compiler=enabled
%ninja_build -C tools src/compiler/clc/mesa_clc src/compiler/spirv/vtn_bindgen2 src/asahi/clc/asahi_clc
export PATH="$PWD/tools/src/compiler/clc:$PWD/tools/src/compiler/spirv:$PWD/tools/src/asahi/clc:$PATH"

# 2. The libraries. Both search both trees' GBM directories, so one build
# serves Fedora's layout and the Arch-style guestos layout (a library of the
# other class fails to load and the next directory is tried).
target=("${common[@]}" -Dllvm=disabled -Dmesa-clc=system -Dprecomp-compiler=system)
CFLAGS="%{build_cflags}" CXXFLAGS="%{build_cxxflags}" LDFLAGS="%{build_ldflags}" \
  meson setup x86_64 "${target[@]}" --libdir=lib64 -Dgbm-backends-path=/usr/lib64/gbm:/usr/lib/gbm
%ninja_build -C x86_64

cat > i686.ini <<'_EOF'
[binaries]
c = ['gcc', '-m32']
cpp = ['g++', '-m32']
ar = 'ar'
strip = 'strip'
pkg-config = 'pkg-config'

[host_machine]
system = 'linux'
cpu_family = 'x86'
cpu = 'i686'
endian = 'little'

[properties]
needs_exe_wrapper = false
pkg_config_libdir = ['/usr/lib/pkgconfig', '/usr/share/pkgconfig']
_EOF
# Fedora's i686 compiler and linker flags, and only i686 pkg-config files
# (rpmbuild exports PKG_CONFIG_PATH for the x86_64 ones).
flags32() { rpm --target i686 --define '_lto_cflags %%{nil}' -E "%%{$1}"; }
CFLAGS="$(flags32 build_cflags)" CXXFLAGS="$(flags32 build_cxxflags)" LDFLAGS="$(flags32 build_ldflags)" \
  PKG_CONFIG_PATH= PKG_CONFIG_SYSTEM_LIBRARY_PATH=/usr/lib meson setup i686 "${target[@]}" --cross-file i686.ini --libdir=lib \
  -Dgbm-backends-path=/usr/lib/gbm:/usr/lib32/gbm -Dglx-read-only-text=true
%ninja_build -C i686

%install
for arch in x86_64 i686; do
  DESTDIR="$PWD/stage-$arch" %{__meson} install -C $arch --no-rebuild
  # No debuginfo packages for files in a private tree: drop debug sections.
  find stage-$arch -type f -name '*.so*' -exec strip --strip-debug {} +
  for lib in stage-$arch/usr/lib*/libgallium-*.so stage-$arch/usr/lib*/libvulkan_asahi.so; do
    grep -aq 'git-%{rev10}' "$lib" || { echo "$lib: no revision stamp" >&2; exit 1; }
  done
done
python3 -I %{SOURCE1} stage-x86_64 stage-i686 %{gravity_git_ref} %{SOURCE2} %{buildroot}%{treedir}

%files
%license docs/license.rst
%doc README.md
%{treedir}/

%changelog
* Tue Nov 10 2026 Niklas Sheth <hi@niklassheth.com>
- First package: the x86 Mesa trees that gravity-x86-mesa and
  fex-guestos-mesa carried as prebuilt payloads, now built here from the
  system Mesa's pinned source together with the guestos tree's Fedora x86
  libraries
