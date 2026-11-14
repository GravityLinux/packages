#!/bin/bash
# Runs in the pinned freedesktop SDK sysroot, without networking.
set -euo pipefail
test "$(uname -m)" = aarch64
cd /build
export PATH=/usr/lib/sdk/llvm22/bin:/usr/bin
export LD_LIBRARY_PATH=/build/deps/lib:/build/deps/lib64:/usr/lib/sdk/llvm22/lib
export PKG_CONFIG_PATH=/build/deps/lib/pkgconfig:/build/deps/lib64/pkgconfig
export PYTHONPATH=/build/pyyaml/lib
export LC_ALL=C.UTF-8
export CFLAGS='-O2 -g0'
export CXXFLAGS='-O2 -g0'
export MESA_GIT_SHA1_OVERRIDE="$1"
# The second argument supports local comparison builds; production uses llvmpipe.
software_driver=${2:-llvmpipe}
case "$software_driver" in
  llvmpipe) runtime_llvm=enabled ;;
  softpipe) runtime_llvm=disabled ;;
  *) echo "Unsupported software driver: $software_driver" >&2; exit 1 ;;
esac
printf '%s\n' "$software_driver" > software-driver.txt

cmake -S spirv-tools -B spirv-build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/build/deps \
  -DSPIRV_SKIP_TESTS=ON -DSPIRV_SKIP_EXECUTABLES=ON \
  -DSPIRV_TOOLS_BUILD_STATIC=ON -DSPIRV_WERROR=OFF \
  -DCMAKE_C_FLAGS_RELEASE='-O2 -DNDEBUG' -DCMAKE_CXX_FLAGS_RELEASE='-O2 -DNDEBUG'
cmake --build spirv-build -j3
cmake --install spirv-build
cmake -S translator -B translator-build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/build/deps \
  -DLLVM_DIR=/usr/lib/sdk/llvm22/lib/cmake/llvm \
  -DLLVM_EXTERNAL_SPIRV_HEADERS_SOURCE_DIR=/build/translator-headers \
  -DLLVM_SPIRV_INCLUDE_TESTS=OFF -DLLVM_SPIRV_BUILD_EXTERNAL=ON \
  -DLLVM_LINK_LLVM_DYLIB=ON -DBUILD_SHARED_LIBS=ON \
  -DCMAKE_CXX_FLAGS_RELEASE='-O2 -DNDEBUG'
cmake --build translator-build -j2
cmake --install translator-build

common=(
  --buildtype=release --wrap-mode=nodownload -Db_ndebug=true -Db_lto=false
  --prefix=/usr/lib/aarch64-linux-gnu/GL/host --libdir=lib
  -Dgallium-drivers=asahi,zink,"$software_driver" -Dvulkan-drivers=asahi
  -Degl=enabled -Dgbm=enabled -Dgles1=enabled -Dgles2=enabled
  -Dglx=dri -Dglvnd=enabled -Dplatforms=x11,wayland
  -Dgallium-va=disabled -Dgallium-rusticl=false -Dbuild-tests=false -Dtools=
  -Dvalgrind=disabled -Dlibunwind=disabled -Dlmsensors=disabled
)
# Shader tools use the pinned SDK's LLVM. llvmpipe uses the same shared library.
meson setup tools mesa "${common[@]}" \
  -Dllvm=enabled -Dshared-llvm=enabled -Dmesa-clc=enabled -Dprecomp-compiler=enabled
ninja -C tools -j3 src/compiler/clc/mesa_clc src/compiler/spirv/vtn_bindgen2 src/asahi/clc/asahi_clc
export PATH=/build/tools/src/compiler/clc:/build/tools/src/compiler/spirv:/build/tools/src/asahi/clc:$PATH

cp /usr/lib/sdk/llvm22/share/licenses/org.freedesktop.Sdk.Extension.llvm22/llvm/LICENSE.TXT LLVM-LICENSE.txt
if [ "$software_driver" = llvmpipe ]; then
  mkdir -p llvm-runtime
  cp /usr/lib/sdk/llvm22/lib/libLLVM.so.22.1 llvm-runtime/
fi
meson setup target mesa "${common[@]}" \
  -Dllvm="$runtime_llvm" -Dshared-llvm=enabled -Dmesa-clc=system -Dprecomp-compiler=system
ninja -C target -j3
DESTDIR=/build/stage meson install -C target --no-rebuild
# Fedora's runtime mounts the extension at lib64/GL, not the freedesktop
# multiarch directory. Reconfigure the paths, rather than pretending that
# changing the ICD JSON is sufficient for EGL/GLX's compiled-in DRI paths.
meson configure target --prefix=/usr/lib64/GL/host
ninja -C target -j3
DESTDIR=/build/stage-fedora meson install -C target --no-rebuild
