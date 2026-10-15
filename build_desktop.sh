#!/bin/bash
# Desktop (Linux) build of tico-beetle-vb with the Vulkan renderer, for testing
# shaders off-device. Needs SDL2, SDL2_mixer, libcurl and a Vulkan driver.
# Run from the repo root; the binary expects to be started from here too
# (it reads tico/fonts, tico/shaders and tico/lang relative to the cwd).
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD="$ROOT/build_desktop"
JOBS=$(nproc)

# Objects live beside the sources and the NRO build leaves aarch64 ones.
make -C "$ROOT" -f Makefile clean platform=unix STATIC_LINKING=1 >/dev/null
make -C "$ROOT" -f Makefile -j"$JOBS" platform=unix STATIC_LINKING=1 STATIC_LINKING_LINK=1 \
    TARGET=mednafen_vb_libretro_unix.a
cmake -S "$ROOT/tico" -B "$BUILD" -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DBEETLE_VB_CORE_LIB="$ROOT/mednafen_vb_libretro_unix.a"
cmake --build "$BUILD" -j"$JOBS"
echo "Built $BUILD/tico-beetle-vb"
