#!/bin/bash
# SPDX-License-Identifier: LGPL-2.1-or-later
set -euo pipefail
: "${WINE_SOURCE:?Set WINE_SOURCE to the correctly patched WineCX checkout}"
: "${RUNTIME_PAYLOAD:?Set RUNTIME_PAYLOAD to your local runtime payload}"
: "${BUILD_DIR:?Set BUILD_DIR to a new build directory}"
: "${OUTPUT_ENGINE:?Set OUTPUT_ENGINE to a new engine directory}"
source_dir=$(cd -- "$WINE_SOURCE" && pwd)
runtime=$(cd -- "$RUNTIME_PAYLOAD" && pwd)
pin=7dbc5b5322a6ef3fb04bdc643c64b188fd641149
test "$(git -C "$source_dir" rev-parse HEAD)" = "$pin"
for target in "$BUILD_DIR" "$OUTPUT_ENGINE"; do
    case "$target" in /*) ;; *) echo 'Output paths must be absolute' >&2; exit 2 ;; esac
    if [ -e "$target" ]; then echo "Refusing existing output: $target" >&2; exit 1; fi
done
export SDKROOT=$(xcrun --sdk macosx --show-sdk-path)
export MACOSX_DEPLOYMENT_TARGET=15.0
export CC='/usr/bin/clang -arch x86_64' CXX='/usr/bin/clang++ -arch x86_64'
export ac_cv_func_pipe2=no
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"
"$source_dir/configure" --host=x86_64-apple-darwin24 --enable-archs=i386,x86_64 \
    --disable-tests --without-x --without-wayland --without-gstreamer --without-ffmpeg \
    --without-freetype --without-gnutls --without-vulkan --without-oss --without-alsa \
    --without-pulse --without-sane --without-usb --without-v4l2 --without-pcap \
    --without-capi --without-opencl --without-cups
make -j8 dlls/ntdll/ntdll.so server/wineserver loader/wine
cp -cR "$runtime" "$OUTPUT_ENGINE"
cp dlls/ntdll/ntdll.so "$OUTPUT_ENGINE/lib/wine/x86_64-unix/ntdll.so"
cp server/wineserver "$OUTPUT_ENGINE/bin/wineserver"
cp loader/wine "$OUTPUT_ENGINE/lib/wine/x86_64-unix/wine"
{
    echo "source=$pin"
    echo 'scope=Unix ntdll, wineserver, loader; remaining payload retained'
    cd "$OUTPUT_ENGINE"
    shasum -a 256 lib/wine/x86_64-unix/ntdll.so bin/wineserver lib/wine/x86_64-unix/wine
} > "$OUTPUT_ENGINE/BO2-BUILD-READY"
