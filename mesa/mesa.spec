%ifnarch s390x
%global with_hardware 1
%global with_kmsro 1
%global with_radeonsi 1
%global with_spirv_tools 1
%global with_vmware 1
%global with_vulkan_hw 1
%if !0%{?rhel}
%global with_r300 1
%global with_r600 1
%global with_opencl 1
%global with_va 1
%endif
%if !0%{?rhel} || 0%{?rhel} >= 9
%global with_nvk %{with_vulkan_hw}
%endif
%global base_vulkan %{?with_vulkan_hw:,amd}%{!?with_vulkan_hw:%{nil}}
%endif

%ifarch aarch64 x86_64
%if !0%{?rhel}
%global with_teflon 1
%endif
%endif

%ifarch %{ix86} x86_64
%global with_crocus 1
%global with_iris   1
%global intel_platform_vulkan %{?with_vulkan_hw:,intel,intel_hasvk}%{!?with_vulkan_hw:%{nil}}
%if !0%{?rhel}
%global with_i915   1
%endif
%endif
%ifarch x86_64
%if 0%{?with_vulkan_hw}
%global with_intel_vk_rt 1
%endif
%endif

%ifarch aarch64 x86_64 %{ix86}
%if !0%{?rhel}
%global with_asahi     1
%global with_d3d12     1
%global with_etnaviv   1
%global with_lima      1
%global with_tegra     1
%global with_vc4       1
%global with_v3d       1
%endif
%global with_freedreno 1
%global with_panfrost  1
%if 0%{?with_asahi}
%global asahi_platform_vulkan %{?with_vulkan_hw:,asahi}%{!?with_vulkan_hw:%{nil}}
%endif
%global extra_platform_vulkan %{?with_vulkan_hw:,broadcom,freedreno,panfrost,imagination}%{!?with_vulkan_hw:%{nil}}
%endif

%if !0%{?rhel}
%global with_libunwind 1
%global with_lmsensors 1
%global with_virtio    1
%endif

%ifarch %{valgrind_arches}
%bcond_without valgrind
%else
%bcond_with valgrind
%endif

%global vulkan_drivers swrast%{?base_vulkan}%{?intel_platform_vulkan}%{?asahi_platform_vulkan}%{?extra_platform_vulkan}%{?with_nvk:,nouveau}%{?with_virtio:,virtio}%{?with_d3d12:,microsoft-experimental}

%if 0%{?with_nvk} && 0%{?rhel}
%global vendor_nvk_crates 1
%endif

# We've gotten a report that enabling LTO for mesa breaks some games. See
# https://bugzilla.redhat.com/show_bug.cgi?id=1862771 for details.
# Disable LTO for now
%global _lto_cflags %nil

# Native extension-only validation need not rebuild the host's many unrelated
# drivers. The default COPR build always builds both host Mesa and the extension.
%bcond_with flatpak_only
%if %{with flatpak_only}
%global with_nvk 0
%global debug_package %{nil}
# assemble.py already strips Mesa. Preserve the prebuilt SDK LLVM unchanged
# in this local extension-only path, which has no debuginfo processing.
%global __brp_strip %{nil}
%global __brp_strip_comment_note %{nil}
%endif

Name:           mesa
Vendor:         Gravity Linux
Summary:        Mesa graphics libraries
Version:        26.3.0~devel
Release:        112.gravity%{?dist}
License:        MIT AND BSD-3-Clause AND SGI-B-2.0
URL:            https://mesa3d.org

# The "Version" field for release candidates has the format: A.B.C~rcX
# However, the tarball has the format: A.B.C-rcX.
# The "ver" variable contains the version in the second format.
%global ver %{gsub %version ~ -}

Source0:        mesa-%{ver}.tar.xz
# src/gallium/auxiliary/postprocess/pp_mlaa* have an ... interestingly worded license.
# Source1 contains email correspondence clarifying the license terms.
# Fedora opts to ignore the optional part of clause 2 and treat that code as 2 clause BSD.
Source1:        Mesa-MLAA-License-Clarification-Email.txt

# Match subprojects/venus-protocol.wrap in the pinned Mesa tree. Git snapshots
# do not bundle this fallback; COPR binary builds must remain offline.
%global venus_protocol_commit e94b12f301b9eb27ebead757128a18420b4f7994
Source2:        https://gitlab.freedesktop.org/virgl/venus-protocol/-/archive/%{venus_protocol_commit}/venus-protocol-%{venus_protocol_commit}.tar.gz

# In CentOS/RHEL, Rust crates required to build NVK are vendored.
# The minimum target versions are obtained from the .wrap files
# https://gitlab.freedesktop.org/mesa/mesa/-/tree/main/subprojects
# but we generally want the latest compatible versions
%global rust_paste_ver 1.0.15
%global rust_proc_macro2_ver 1.0.106
%global rust_quote_ver 1.0.44
%global rust_syn_ver 2.0.115
%global rust_unicode_ident_ver 1.0.23
%global rustc_hash_ver 2.1.1
Source10:       https://crates.io/api/v1/crates/paste/%{rust_paste_ver}/download#/paste-%{rust_paste_ver}.tar.gz
Source11:       https://crates.io/api/v1/crates/proc-macro2/%{rust_proc_macro2_ver}/download#/proc-macro2-%{rust_proc_macro2_ver}.tar.gz
Source12:       https://crates.io/api/v1/crates/quote/%{rust_quote_ver}/download#/quote-%{rust_quote_ver}.tar.gz
Source13:       https://crates.io/api/v1/crates/syn/%{rust_syn_ver}/download#/syn-%{rust_syn_ver}.tar.gz
Source14:       https://crates.io/api/v1/crates/unicode-ident/%{rust_unicode_ident_ver}/download#/unicode-ident-%{rust_unicode_ident_ver}.tar.gz
Source15:       https://crates.io/api/v1/crates/rustc-hash/%{rustc_hash_ver}/download#/rustc-hash-%{rustc_hash_ver}.tar.gz

# Pinned Flatpak compiler acquisition; only aarch64 produces the extension.
# These are build tools, not prebuilt Gravity Mesa. Mesa is always Source0.
Source90:       gravity-flatpak-build.sh
Source91:       gravity-flatpak-sandbox.sh
Source92:       gravity-flatpak-assemble.py
Source93:       https://codeload.github.com/KhronosGroup/SPIRV-Tools/tar.gz/refs/tags/v2026.4#/flatpak-spirv-tools.tar.gz
Source94:       https://codeload.github.com/KhronosGroup/SPIRV-Headers/tar.gz/496543121ce6419f23d6fa5d7194ba66c36212d2#/flatpak-spirv-headers.tar.gz
Source95:       https://codeload.github.com/KhronosGroup/SPIRV-LLVM-Translator/tar.gz/ae707ecba4b0c64d85f4f7bdcabeb1fa152c0ab2#/flatpak-translator.tar.gz
Source96:       https://codeload.github.com/KhronosGroup/SPIRV-Headers/tar.gz/cb42dec3830d3ac67fa449ecdc0c0f73d5e74498#/flatpak-translator-headers.tar.gz
Source97:       https://files.pythonhosted.org/packages/05/8e/961c0007c59b8dd7729d542c61a4d537767a59645b82a0b521206e1e25c2/pyyaml-6.0.3.tar.gz
Source98:       gravity-flatpak-sdk.sha256
Source99:       gravity-flatpak-export-sdk.py
Source100:      gravity-flatpak-sdk.lock.json
Source101:      gravity-flatpak-llvm-origin.json

%ifarch aarch64
# The one prebuilt SDK libLLVM.so.22.1 has no GNU build ID. It is shipped
# byte-for-byte, mode 0644, so find-debuginfo leaves it untouched.
%global _missing_build_ids_terminate_build 0
%endif

# Never derive system RPM dependencies/provides from the private SDK ABI.
%global __provides_exclude_from ^/var/lib/flatpak/extension/.*$
%global __requires_exclude_from ^/var/lib/flatpak/extension/.*$
%ifarch aarch64
BuildRequires:  bubblewrap
BuildRequires:  patchelf
BuildRequires:  flatpak
BuildRequires:  python3
BuildRequires:  binutils
%endif

%if %{without flatpak_only}
BuildRequires:  meson >= 1.4.0
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  libstdc++-static
BuildRequires:  gettext
%if 0%{?with_hardware}
BuildRequires:  kernel-headers
BuildRequires:  systemd-devel
%endif
# We only check for the minimum version of pkgconfig(libdrm) needed so that the
# SRPMs for each arch still have the same build dependencies. See:
# https://bugzilla.redhat.com/show_bug.cgi?id=1859515
BuildRequires:  pkgconfig(libdrm) >= 2.4.133
%if 0%{?with_libunwind}
BuildRequires:  pkgconfig(libunwind)
%endif
BuildRequires:  pkgconfig(expat)
BuildRequires:  pkgconfig(zlib) >= 1.2.3
BuildRequires:  pkgconfig(libzstd)
BuildRequires:  pkgconfig(wayland-scanner)
BuildRequires:  pkgconfig(wayland-protocols) >= 1.41
BuildRequires:  pkgconfig(wayland-client) >= 1.11
BuildRequires:  pkgconfig(wayland-server) >= 1.11
BuildRequires:  pkgconfig(wayland-egl-backend) >= 3
BuildRequires:  pkgconfig(libdisplay-info)
BuildRequires:  pkgconfig(x11)
BuildRequires:  pkgconfig(xext)
BuildRequires:  pkgconfig(xdamage) >= 1.1
BuildRequires:  pkgconfig(xfixes)
BuildRequires:  pkgconfig(xcb-glx) >= 1.8.1
BuildRequires:  pkgconfig(xxf86vm)
BuildRequires:  pkgconfig(xcb)
BuildRequires:  pkgconfig(x11-xcb)
BuildRequires:  pkgconfig(xcb-dri2) >= 1.8
BuildRequires:  pkgconfig(xcb-dri3)
BuildRequires:  pkgconfig(xcb-present)
BuildRequires:  pkgconfig(xcb-sync)
BuildRequires:  pkgconfig(xshmfence) >= 1.1
BuildRequires:  pkgconfig(dri2proto) >= 2.8
BuildRequires:  pkgconfig(glproto) >= 1.4.14
BuildRequires:  pkgconfig(xcb-xfixes)
BuildRequires:  pkgconfig(xcb-randr)
BuildRequires:  pkgconfig(xrandr) >= 1.3
BuildRequires:  bison
BuildRequires:  flex
%if 0%{?with_lmsensors}
BuildRequires:  lm_sensors-devel
%endif
%if 0%{?with_va}
BuildRequires:  pkgconfig(libva) >= 0.38.0
%endif
BuildRequires:  pkgconfig(libelf)
BuildRequires:  pkgconfig(libglvnd) >= 1.3.2
BuildRequires:  llvm-devel >= 7.0.0
%if 0%{?with_teflon}
BuildRequires:  flatbuffers-devel
BuildRequires:  flatbuffers-compiler
BuildRequires:  xtensor-devel
%endif
%if 0%{?with_opencl} || 0%{?with_nvk} || 0%{?with_asahi} || 0%{?with_panfrost}
BuildRequires:  clang-devel
BuildRequires:  pkgconfig(libclc)
BuildRequires:  pkgconfig(SPIRV-Tools)
BuildRequires:  pkgconfig(LLVMSPIRVLib)
%endif
%if 0%{?with_opencl} || 0%{?with_nvk}
BuildRequires:  bindgen
%if 0%{?rhel}
BuildRequires:  rust-toolset
%else
BuildRequires:  cargo-rpm-macros
%endif
%endif
%if 0%{?with_opencl}
BuildRequires:  libstdc++-static
%endif
%if 0%{?with_nvk}
BuildRequires:  cbindgen
%endif
%if %{with valgrind}
BuildRequires:  pkgconfig(valgrind)
%endif
BuildRequires:  python3-devel
BuildRequires:  python3-mako
BuildRequires:  python3-pycparser
BuildRequires:  python3-pyyaml
BuildRequires:  vulkan-headers
BuildRequires:  glslang
%if 0%{?with_vulkan_hw}
BuildRequires:  pkgconfig(vulkan)
%endif
%if 0%{?with_d3d12}
BuildRequires:  pkgconfig(DirectX-Headers) >= 1.619.1
%endif

%endif

%description
%{summary}.

%if %{without flatpak_only}
%package filesystem
Summary:        Mesa driver filesystem
Provides:       mesa-dri-filesystem = %{?epoch:%{epoch}:}%{version}-%{release}
Obsoletes:      mesa-omx-drivers < %{?epoch:%{epoch}:}%{version}-%{release}
Obsoletes:      mesa-libd3d < %{?epoch:%{epoch}:}%{version}-%{release}
Obsoletes:      mesa-libd3d-devel < %{?epoch:%{epoch}:}%{version}-%{release}
Obsoletes:      mesa-vdpau-drivers < %{?epoch:%{epoch}:}%{version}-%{release}

%description filesystem
%{summary}.

%package libGL
Summary:        Mesa libGL runtime libraries
Requires:       libglvnd-glx%{?_isa} >= 1:1.3.2
Requires:       %{name}-dri-drivers%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
Obsoletes:      %{name}-libOSMesa < 25.1.0~rc2-1

%description libGL
%{summary}.

%package libGL-devel
Summary:        Mesa libGL development package
Requires:       (%{name}-libGL%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release} if %{name}-libGL%{?_isa})
Requires:       libglvnd-devel%{?_isa} >= 1:1.3.2
Provides:       libGL-devel = %{?epoch:%{epoch}:}%{version}-%{release}
Provides:       libGL-devel%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
Recommends:     gl-manpages
Obsoletes:      %{name}-libOSMesa-devel < 25.1.0~rc2-1

%description libGL-devel
%{summary}.

%package libEGL
Summary:        Mesa libEGL runtime libraries
Requires:       libglvnd-egl%{?_isa} >= 1:1.3.2
Requires:       %{name}-libgbm%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
Requires:       %{name}-dri-drivers%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}

%description libEGL
%{summary}.

%package libEGL-devel
Summary:        Mesa libEGL development package
Requires:       (%{name}-libEGL%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release} if %{name}-libEGL%{?_isa})
Requires:       libglvnd-devel%{?_isa} >= 1:1.3.2
Requires:       %{name}-khr-devel%{?_isa}
Provides:       libEGL-devel = %{?epoch:%{epoch}:}%{version}-%{release}
Provides:       libEGL-devel%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}

%description libEGL-devel
%{summary}.

%package dri-drivers
Summary:        Mesa-based DRI drivers
Requires:       %{name}-filesystem%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
Requires:       %{name}-libgbm%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
Obsoletes:      %{name}-libglapi < 25.0.0~rc2-1
Obsoletes:      %{name}-va-drivers < 26.0.0-5
Provides:       %{name}-va-drivers = %{?epoch:%{epoch}:}%{version}-%{release}
Provides:       %{name}-va-drivers%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
Obsoletes:      %{name}-vaapi-drivers < 22.2.0-5
# The pinned Mesa revision (first 10 hex digits): gravity-x86-mesa and
# fex-guestos-mesa carry x86 builds of exactly this revision and require it.
%if %{defined gravity_git_ref}
Provides:       gravity-mesa-revision = %{lua:print(string.sub(rpm.expand("%{gravity_git_ref}"), 1, 10))}
%endif

%description dri-drivers
%{summary}.

%package libgbm
Summary:        Mesa gbm runtime library
Provides:       libgbm = %{?epoch:%{epoch}:}%{version}-%{release}
Provides:       libgbm%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
Recommends:     %{name}-dri-drivers%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
# If mesa-dri-drivers are installed, they must match in version. This is here to prevent using
# older mesa-dri-drivers together with a newer mesa-libgbm and its dependants.
# See https://bugzilla.redhat.com/show_bug.cgi?id=2193135 .
Requires:       (%{name}-dri-drivers%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release} if %{name}-dri-drivers%{?_isa})

%description libgbm
%{summary}.

%package libgbm-devel
Summary:        Mesa libgbm development package
Requires:       %{name}-libgbm%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
Provides:       libgbm-devel = %{?epoch:%{epoch}:}%{version}-%{release}
Provides:       libgbm-devel%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}

%description libgbm-devel
%{summary}.

%if 0%{?with_opencl}
%package libOpenCL
Summary:        Mesa OpenCL runtime library
Requires:       (ocl-icd%{?_isa} or OpenCL-ICD-Loader%{?_isa})
Requires:       libclc%{?_isa}
Requires:       %{name}-libgbm%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
Requires:       opencl-filesystem

%description libOpenCL
%{summary}.

%package libOpenCL-devel
Summary:        Mesa OpenCL development package
Requires:       %{name}-libOpenCL%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}

%description libOpenCL-devel
%{summary}.
%endif

%if 0%{?with_teflon}
%package libTeflon
Summary:        Mesa TensorFlow Lite delegate

%description libTeflon
%{summary}.
%endif

%if 0%{?with_d3d12}
%package dxil-devel
Summary:        Mesa SPIR-V to DXIL binary
Requires:       %{name}-filesystem%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}

%description dxil-devel
Development tools for translating SPIR-V shader code to DXIL for Direct3D 12
%endif

%package vulkan-drivers
Summary:        Mesa Vulkan drivers
%if 0%{?with_virtio}
Provides:       bundled(venus-protocol) = 1.1
%endif
Requires:       vulkan%{_isa}
Requires:       %{name}-filesystem%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
Obsoletes:      mesa-vulkan-devel < %{?epoch:%{epoch}:}%{version}-%{release}
Obsoletes:      VK_hdr_layer < 1

%description vulkan-drivers
The drivers with support for the Vulkan API.
%endif

%ifarch aarch64
%package -n gravity-flatpak-graphics
Summary:        Gravity hardware graphics drivers for Flatpak applications
License:        MIT AND BSD-3-Clause AND SGI-B-2.0 AND Apache-2.0 AND (Apache-2.0 WITH LLVM-exception)
Requires:       flatpak
Requires:       gravity-mesa-revision = %{lua:print(string.sub(rpm.expand("%{gravity_git_ref}"), 1, 10))}
Provides:       gravity-flatpak-graphics(git-ref) = %{gravity_git_ref}

%description -n gravity-flatpak-graphics
Gravity's native Apple GPU GL, GLES and Vulkan drivers, built from this
Mesa source in the freedesktop SDK. Automatically selected GL.host extensions
for freedesktop 25.08 and 26.08 (including derived KDE runtimes) and Fedora f45.
No environment override or software rendering default is installed.
Explicit software GL requests use llvmpipe with the pinned SDK's shared LLVM.
%endif

%prep
%autosetup -n %{name}-%{ver} -p1
cp %{SOURCE1} docs/

%ifarch aarch64
mkdir flatpak
mkdir flatpak/mesa flatpak/spirv-tools flatpak/translator flatpak/translator-headers flatpak/pyyaml
tar -xf %{SOURCE0} --strip-components=1 -C flatpak/mesa
tar -xf %{SOURCE93} --strip-components=1 -C flatpak/spirv-tools
mkdir -p flatpak/spirv-tools/external/spirv-headers
tar -xf %{SOURCE94} --strip-components=1 -C flatpak/spirv-tools/external/spirv-headers
tar -xf %{SOURCE95} --strip-components=1 -C flatpak/translator
tar -xf %{SOURCE96} --strip-components=1 -C flatpak/translator-headers
tar -xf %{SOURCE97} --strip-components=1 -C flatpak/pyyaml
cp %{SOURCE90} flatpak/build.sh
cp %{SOURCE99} flatpak/export-sdk.py
cp %{SOURCE100} flatpak/sdk.lock.json
cp %{SOURCE101} flatpak/llvm-origin.json
%endif

# Fail rather than silently using stale vendored protocol after a Mesa repin.
grep -Fx 'revision = %{venus_protocol_commit}' subprojects/venus-protocol.wrap
grep -Fx 'directory = venus-protocol-1.1' subprojects/venus-protocol.wrap
tar -xf %{SOURCE2} -C subprojects/
mv subprojects/venus-protocol-%{venus_protocol_commit} subprojects/venus-protocol-1.1

# Extract Rust crates meson cache directory
%if 0%{?vendor_nvk_crates}
mkdir subprojects/packagecache/
tar -xvf %{SOURCE10} -C subprojects/packagecache/
tar -xvf %{SOURCE11} -C subprojects/packagecache/
tar -xvf %{SOURCE12} -C subprojects/packagecache/
tar -xvf %{SOURCE13} -C subprojects/packagecache/
tar -xvf %{SOURCE14} -C subprojects/packagecache/
tar -xvf %{SOURCE15} -C subprojects/packagecache/
for d in subprojects/packagecache/*-*; do
    echo '{"files":{}}' > $d/.cargo-checksum.json
done
%endif

%if 0%{?with_nvk}
cat > Cargo.toml <<_EOF
[package]
name = "mesa"
version = "%{ver}"
edition = "2021"

[lib]
path = "src/nouveau/nil/lib.rs"

# only direct dependencies need to be listed here
[dependencies]
paste = "$(grep ^directory subprojects/paste*.wrap | sed 's|.*-||')"
syn = { version = "$(grep ^directory subprojects/syn*.wrap | sed 's|.*-||')", features = ["clone-impls"] }
rustc-hash = "$(grep ^directory subprojects/rustc-hash*.wrap | sed 's|.*-||')"
_EOF
%if 0%{?vendor_nvk_crates}
%cargo_prep -v subprojects/packagecache
%else
%cargo_prep

%generate_buildrequires
%cargo_generate_buildrequires
%endif
%endif


%build
%ifarch aarch64
# COPR needs --enable-net on for SDK acquisition. The compiler sandbox below
# still has no network. Nothing from the build worker's system ABI is shipped.
python3 flatpak/export-sdk.py --output "$PWD/flatpak/gravity-flatpak-sdk-25.08-aarch64.tar.gz"
(
  cd flatpak
  # Hash the normalized contents, not gzip's compressor-dependent encoding.
  read -r sdk_want sdk_name < %{SOURCE98}
  sdk_have=$(gzip -dc gravity-flatpak-sdk-25.08-aarch64.tar.gz | sha256sum | cut -d ' ' -f1)
  echo "Flatpak SDK contents SHA256: $sdk_have"
  test "$sdk_have" = "$sdk_want" || { echo 'Flatpak SDK content checksum mismatch' >&2; exit 1; }
  # The SDK tree is archived read-only and the LLVM extension lands inside it:
  # an unprivileged builder can only create it if directory modes are applied
  # last. Then make the tree writable by its owner so the build directory can
  # be removed; the compiler sandbox still mounts it read-only.
  tar --delay-directory-restore -xf gravity-flatpak-sdk-25.08-aarch64.tar.gz
  chmod -R u+w sdk
  rm gravity-flatpak-sdk-25.08-aarch64.tar.gz
)
%endif
%if %{without flatpak_only}
# ensure standard Rust compiler flags are set
export RUSTFLAGS="%build_rustflags"
# The release tarball has no .git, so Mesa's version string would lack the
# "(git-xxxxxxxxxx)" suffix that identifies the pinned source in bug reports.
# tools/package.py defines gravity_git_ref from sources.json.
%{?gravity_git_ref:export MESA_GIT_SHA1_OVERRIDE=%{gravity_git_ref}}

%if 0%{?with_nvk}
# So... Meson can't actually find them without tweaks
%if !0%{?vendor_nvk_crates}
export MESON_PACKAGE_CACHE_DIR="%{cargo_registry}/"
%endif

# This function rewrites a mesa .wrap file:
# - Removes the lines that start with "source"
# - Replaces the "directory =" with the MESON_PACKAGE_CACHE_DIR
#
# Example: An upstream .wrap file like this (proc-macro2-1-rs.wrap):
#
# [wrap-file]
# directory = proc-macro2-1.0.86
# source_url = https://crates.io/api/v1/crates/proc-macro2/1.0.86/download
# source_filename = proc-macro2-1.0.86.tar.gz
# source_hash = 5e719e8df665df0d1c8fbfd238015744736151d4445ec0836b8e628aae103b77
# patch_directory = proc-macro2-1-rs
#
# Will be transformed to:
#
# [wrap-file]
# directory = meson-package-cache-dir
# patch_directory = proc-macro2-1-rs
rewrite_wrap_file() {
  sed -e "/source.*/d" -e "s/^directory = ${1}-.*/directory = $(basename ${MESON_PACKAGE_CACHE_DIR:-subprojects/packagecache}/${1}-*)/" -i subprojects/${1}*.wrap
}

rewrite_wrap_file proc-macro2
rewrite_wrap_file quote
rewrite_wrap_file syn
rewrite_wrap_file unicode-ident
rewrite_wrap_file paste
rewrite_wrap_file rustc-hash
%endif

%meson \
  -Dplatforms=x11,wayland \
%if 0%{?with_hardware}
  -Dgallium-drivers=llvmpipe,virgl,nouveau%{?with_r300:,r300}%{?with_crocus:,crocus}%{?with_i915:,i915}%{?with_iris:,iris}%{?with_vmware:,svga}%{?with_radeonsi:,radeonsi}%{?with_r600:,r600}%{?with_asahi:,asahi}%{?with_freedreno:,freedreno}%{?with_etnaviv:,etnaviv}%{?with_tegra:,tegra}%{?with_vc4:,vc4}%{?with_v3d:,v3d}%{?with_lima:,lima}%{?with_panfrost:,panfrost}%{?with_vulkan_hw:,zink}%{?with_d3d12:,d3d12}%{?with_teflon:,ethosu,rocket} \
%else
  -Dgallium-drivers=llvmpipe,virgl \
%endif
  -Dgallium-va=%{?with_va:enabled}%{!?with_va:disabled} \
  -Dgallium-mediafoundation=disabled \
  -Dteflon=%{?with_teflon:true}%{!?with_teflon:false} \
%if 0%{?with_opencl}
  -Dgallium-rusticl=true \
%endif
  -Dvulkan-drivers=%{?vulkan_drivers} \
  -Dvulkan-layers=device-select,anti-lag \
  -Dgles1=enabled \
  -Dgles2=enabled \
  -Dopengl=true \
  -Dgbm=enabled \
  -Dglx=dri \
  -Degl=enabled \
  -Dglvnd=enabled \
  -Dintel-rt=%{?with_intel_vk_rt:enabled}%{!?with_intel_vk_rt:disabled} \
  -Dmicrosoft-clc=disabled \
  -Dllvm=enabled \
  -Dshared-llvm=enabled \
  -Dvalgrind=%{?with_valgrind:enabled}%{!?with_valgrind:disabled} \
  -Dbuild-tests=false \
%if !0%{?with_libunwind}
  -Dlibunwind=disabled \
%endif
%if !0%{?with_lmsensors}
  -Dlmsensors=disabled \
%endif
  -Dandroid-libbacktrace=disabled \
%ifarch %{ix86}
  -Dglx-read-only-text=true \
%endif
  -Dspirv-tools=%{?with_spirv_tools:enabled}%{!?with_spirv_tools:disabled} \
  %{nil}
%meson_build
%endif

%ifarch aarch64
(cd flatpak; sh %{SOURCE91} %{gravity_git_ref})
%endif

%if 0%{?with_nvk}
%cargo_license_summary
%{cargo_license} > LICENSE.dependencies
%if 0%{?vendor_nvk_crates}
%cargo_vendor_manifest
%endif
%endif

%install
%if %{without flatpak_only}
%meson_install
%endif

%ifarch aarch64
python3 -I %{SOURCE92} flatpak %{buildroot}/var/lib/flatpak/extension %{gravity_git_ref}
%endif

%if %{without flatpak_only}
# likewise glvnd
rm -vf %{buildroot}%{_libdir}/libGLX_mesa.so
rm -vf %{buildroot}%{_libdir}/libEGL_mesa.so
# XXX can we just not build this
rm -vf %{buildroot}%{_libdir}/libGLES*

%if ! 0%{?with_asahi}
# This symlink is unconditionally created when any kmsro driver is enabled
# We don't want this one so delete it
rm -vf %{buildroot}%{_libdir}/dri/apple_dri.so
%endif

# glvnd needs a default provider for indirect rendering where it cannot
# determine the vendor
ln -s libGLX_mesa.so.0 %{buildroot}%{_libdir}/libGLX_system.so.0
%endif

%ifarch aarch64
%files -n gravity-flatpak-graphics
%license docs/license.rst
%license flatpak/LLVM-LICENSE.txt flatpak/spirv-tools/LICENSE
/var/lib/flatpak/extension/org.freedesktop.Platform.GL.host/
/var/lib/flatpak/extension/org.fedoraproject.Platform.GL.host/
%endif

%if %{without flatpak_only}
%files filesystem
%doc docs/Mesa-MLAA-License-Clarification-Email.txt
%dir %{_libdir}/dri
%dir %{_datadir}/drirc.d

%files libGL
%{_libdir}/libGLX_mesa.so.0*
%{_libdir}/libGLX_system.so.0*
%files libGL-devel
%dir %{_includedir}/GL
%dir %{_includedir}/GL/internal
%{_includedir}/GL/internal/dri_interface.h
%{_libdir}/pkgconfig/dri.pc

%files libEGL
%{_datadir}/glvnd/egl_vendor.d/50_mesa.json
%{_libdir}/libEGL_mesa.so.0*
%files libEGL-devel
%dir %{_includedir}/EGL
%{_includedir}/EGL/eglext_angle.h
%{_includedir}/EGL/eglmesaext.h

%files libgbm
%{_libdir}/libgbm.so.1
%{_libdir}/libgbm.so.1.*
%files libgbm-devel
%{_libdir}/libgbm.so
%{_includedir}/gbm.h
%{_includedir}/gbm_backend_abi.h
%{_libdir}/pkgconfig/gbm.pc

%if 0%{?with_teflon}
%files libTeflon
%{_libdir}/libteflon.so
%endif

%if 0%{?with_opencl}
%files libOpenCL
%{_libdir}/libRusticlOpenCL.so.*
%{_sysconfdir}/OpenCL/vendors/rusticl.icd

%files libOpenCL-devel
%{_libdir}/libRusticlOpenCL.so
%endif

%files dri-drivers
%{_datadir}/drirc.d/00-mesa-defaults.conf
%{_libdir}/libgallium-*.so
%{_libdir}/gbm/dri_gbm.so
%{_libdir}/dri/kms_swrast_dri.so
%{_libdir}/dri/libdril_dri.so
%{_libdir}/dri/swrast_dri.so
%{_libdir}/dri/virtio_gpu_dri.so
%{_datadir}/drirc.d/00-virtio_gpu-defaults.conf

%if 0%{?with_hardware}
%if 0%{?with_r300}
%{_libdir}/dri/r300_dri.so
%{_datadir}/drirc.d/00-r300-defaults.conf
%endif
%if 0%{?with_radeonsi}
%if 0%{?with_r600}
%{_libdir}/dri/r600_dri.so
%{_datadir}/drirc.d/00-r600-defaults.conf
%endif
%{_libdir}/dri/radeonsi_dri.so
%{_datadir}/drirc.d/00-radeonsi-defaults.conf
%endif
%ifarch %{ix86} x86_64
%{_libdir}/dri/crocus_dri.so
%{_datadir}/drirc.d/00-crocus-defaults.conf
%{_libdir}/dri/iris_dri.so
%{_datadir}/drirc.d/00-iris-defaults.conf
%if 0%{?with_i915}
%{_libdir}/dri/i915_dri.so
%endif
%endif
%ifnarch s390x
%if 0%{?with_asahi}
%{_libdir}/dri/apple_dri.so
%{_libdir}/dri/asahi_dri.so
%{_datadir}/drirc.d/00-asahi-defaults.conf
%endif
%if 0%{?with_d3d12}
%{_libdir}/dri/d3d12_dri.so
%{_datadir}/drirc.d/00-d3d12-defaults.conf
%endif
%{_libdir}/dri/ingenic-drm_dri.so
%{_libdir}/dri/imx-drm_dri.so
%{_libdir}/dri/imx-lcdif_dri.so
%{_libdir}/dri/kirin_dri.so
%{_libdir}/dri/komeda_dri.so
%{_libdir}/dri/mali-dp_dri.so
%{_libdir}/dri/mcde_dri.so
%{_libdir}/dri/mxsfb-drm_dri.so
%{_libdir}/dri/rcar-du_dri.so
%{_libdir}/dri/stm_dri.so
%endif
%if 0%{?with_vc4}
%{_libdir}/dri/vc4_dri.so
%endif
%if 0%{?with_v3d}
%{_libdir}/dri/v3d_dri.so
%{_datadir}/drirc.d/00-v3d-defaults.conf
%endif
%if 0%{?with_freedreno}
%{_libdir}/dri/kgsl_dri.so
%{_libdir}/dri/msm_dri.so
%{_datadir}/drirc.d/00-msm-defaults.conf
%endif
%if 0%{?with_etnaviv}
%{_libdir}/dri/etnaviv_dri.so
%endif
%if 0%{?with_tegra}
%{_libdir}/dri/tegra_dri.so
%endif
%if 0%{?with_lima}
%{_libdir}/dri/lima_dri.so
%endif
%if 0%{?with_panfrost}
%{_libdir}/dri/panfrost_dri.so
%{_libdir}/dri/panthor_dri.so
%{_datadir}/drirc.d/00-panfrost-defaults.conf
%endif
%{_libdir}/dri/nouveau_dri.so
%if 0%{?with_vmware}
%{_libdir}/dri/vmwgfx_dri.so
%{_datadir}/drirc.d/00-vmwgfx-defaults.conf
%endif
%endif
%if 0%{?with_kmsro}
%{_libdir}/dri/armada-drm_dri.so
%{_libdir}/dri/exynos_dri.so
%{_libdir}/dri/gm12u320_dri.so
%{_libdir}/dri/hdlcd_dri.so
%{_libdir}/dri/hx8357d_dri.so
%{_libdir}/dri/ili9163_dri.so
%{_libdir}/dri/ili9225_dri.so
%{_libdir}/dri/ili9341_dri.so
%{_libdir}/dri/ili9486_dri.so
%{_libdir}/dri/imx-dcss_dri.so
%{_libdir}/dri/mediatek_dri.so
%{_libdir}/dri/meson_dri.so
%{_libdir}/dri/mi0283qt_dri.so
%{_libdir}/dri/panel-mipi-dbi_dri.so
%{_libdir}/dri/pl111_dri.so
%{_libdir}/dri/repaper_dri.so
%{_libdir}/dri/rockchip_dri.so
%{_libdir}/dri/rzg2l-du_dri.so
%{_libdir}/dri/ssd130x_dri.so
%{_libdir}/dri/st7586_dri.so
%{_libdir}/dri/st7735r_dri.so
%{_libdir}/dri/sti_dri.so
%{_libdir}/dri/sun4i-drm_dri.so
%{_libdir}/dri/udl_dri.so
%{_libdir}/dri/vkms_dri.so
%{_libdir}/dri/zynqmp-dpsub_dri.so
%endif
%if 0%{?with_vulkan_hw}
%{_libdir}/dri/zink_dri.so
%{_datadir}/drirc.d/00-zink-defaults.conf
%endif
%if 0%{?with_va}
%{_libdir}/dri/nouveau_drv_video.so
%if 0%{?with_r600}
%{_libdir}/dri/r600_drv_video.so
%endif
%if 0%{?with_radeonsi}
%{_libdir}/dri/radeonsi_drv_video.so
%endif
%if 0%{?with_d3d12}
%{_libdir}/dri/d3d12_drv_video.so
%endif
%{_libdir}/dri/virtio_gpu_drv_video.so
%endif

%if 0%{?with_d3d12}
%files dxil-devel
%{_bindir}/spirv2dxil
%{_libdir}/libspirv_to_dxil.a
%{_libdir}/libspirv_to_dxil.so
%endif

%files vulkan-drivers
%if 0%{?with_nvk}
%license LICENSE.dependencies
%if 0%{?vendor_nvk_crates}
%license cargo-vendor.txt
%endif
%endif
%{_libdir}/libvulkan_lvp.so
%{_datadir}/vulkan/icd.d/lvp_icd.*.json
%{_datadir}/drirc.d/00-lavapipe-defaults.conf
%{_libdir}/libVkLayer_MESA_device_select.so
%{_datadir}/vulkan/implicit_layer.d/VkLayer_MESA_device_select.json
%{_libdir}/libVkLayer_MESA_anti_lag.so
%{_datadir}/vulkan/implicit_layer.d/VkLayer_MESA_anti_lag.json
%if 0%{?with_virtio}
%{_libdir}/libvulkan_virtio.so
%{_datadir}/vulkan/icd.d/virtio_icd.*.json
%{_datadir}/drirc.d/00-venus-defaults.conf
%endif
%if 0%{?with_vulkan_hw}
%{_libdir}/libvulkan_radeon.so
%{_datadir}/drirc.d/00-radv-defaults.conf
%{_datadir}/vulkan/icd.d/radeon_icd.*.json
%if 0%{?with_nvk}
%{_libdir}/libvulkan_nouveau.so
%{_datadir}/vulkan/icd.d/nouveau_icd.*.json
%{_datadir}/drirc.d/00-nvk-defaults.conf
%endif
%if 0%{?with_d3d12}
%{_libdir}/libvulkan_dzn.so
%{_datadir}/vulkan/icd.d/dzn_icd.*.json
%{_datadir}/drirc.d/00-dzn-defaults.conf
%endif
%ifarch %{ix86} x86_64
%{_libdir}/libvulkan_intel.so
%{_datadir}/vulkan/icd.d/intel_icd.*.json
%{_datadir}/drirc.d/00-anv-defaults.conf
%{_libdir}/libvulkan_intel_hasvk.so
%{_datadir}/vulkan/icd.d/intel_hasvk_icd.*.json
%{_datadir}/drirc.d/00-hasvk-defaults.conf
%endif
%ifarch aarch64 x86_64 %{ix86}
%if 0%{?with_asahi}
%{_libdir}/libvulkan_asahi.so
%{_datadir}/vulkan/icd.d/asahi_icd.*.json
%{_datadir}/drirc.d/00-hk-defaults.conf
%endif
%{_libdir}/libvulkan_broadcom.so
%{_datadir}/vulkan/icd.d/broadcom_icd.*.json
%{_datadir}/drirc.d/00-v3dv-defaults.conf
%{_libdir}/libvulkan_freedreno.so
%{_datadir}/vulkan/icd.d/freedreno_icd.*.json
%{_datadir}/drirc.d/00-turnip-defaults.conf
%{_libdir}/libvulkan_panfrost.so
%{_datadir}/vulkan/icd.d/panfrost_icd.*.json
%{_datadir}/drirc.d/00-panvk-defaults.conf
%{_libdir}/libvulkan_powervr_mesa.so
%{_datadir}/vulkan/icd.d/powervr_mesa_icd.*.json
%{_datadir}/drirc.d/00-pvr-defaults.conf
%endif
%endif

%endif

%changelog
* Fri Nov 13 2026 Niklas Sheth <hi@niklassheth.com> - 26.3.0~devel-112.gravity
- Restore software GL in Flatpak with llvmpipe and the pinned SDK's shared LLVM.
- Declare the linked SPIRV-Tools and LLVM licenses for the graphics extension.
- Preserve SDK LLVM byte-for-byte and tolerate its missing GNU build ID.

* Thu Nov 12 2026 Niklas Sheth <hi@niklassheth.com> - 26.3.0~devel-111.gravity
- Build Gravity Flatpak hardware graphics extensions from the same Mesa source
  for freedesktop 25.08/26.08 and Fedora f45, with an offline pinned SDK.

* Wed Nov 11 2026 Niklas Sheth <hi@niklassheth.com> - 26.3.0~devel-110.gravity
- Fix intermittently misplaced vertices: the shader compiler now waits for a
  scalar export before reusing its inputs (seen as flickering spikes on user
  interface elements in Direct3D games).

* Tue Nov 10 2026 Niklas Sheth <hi@niklassheth.com> - 26.3.0~devel-109.gravity
- Fix vertex-stage store ordering in the Vulkan driver, stop printing the
  conformance warning.

* Mon Nov 09 2026 Niklas Sheth <niklassheth@gmail.com> - 26.3.0~devel-108.gravity
- Pin GravityLinux/mesa 533a2be5
- CPU maps of shared dma-bufs wait for their implicit fences, so screen
  recorders such as KRdp no longer capture half-rendered compositor frames
- The version string names the pinned commit (MESA_GIT_SHA1_OVERRIDE)
- dri-drivers: Provides gravity-mesa-revision = <pinned revision>, which the
  x86 Mesa trees (gravity-x86-mesa, fex-guestos-mesa) require

* Sun Sep 27 2026 Gravity Linux maintainers - 26.3.0~devel-103.gravity
- Update Mesa source pin to include ordinary varying export for legacy clip vertex

* Fri Sep 18 2026 Gravity Linux maintainers - 26.3.0~devel-102.gravity
- Pin published M4 compiler and driver updates with automatic Apple9 rendering

* Wed Sep 16 2026 Gravity Linux maintainers - 26.3.0~devel-101.gravity
- Bundle the pinned Venus protocol fallback for offline builds

* Wed Sep 16 2026 Gravity Linux maintainers - 26.3.0~devel-100.gravity
- Pin Gravity main at 4bd3d1801ae6 for preliminary hardware image testing
- Align the source version and minimum Meson version with the snapshot

* Tue Sep 15 2026 Gravity Linux maintainers - 26.2.2-100.gravity
- Prepare downstream Gravity Mesa packaging
