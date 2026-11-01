#!/usr/bin/env bash
# =============================================================================
#  Build the C++ MotionGloveSDK (third_party/MotionGloveSDK_cpp) into
#  build/mgsdk_cpp/install/{bin,lib} so that src/native can load it.
#
#  Usage:
#    bash "scripts/[Linux]build_mgsdk_cpp.sh" [Release|Debug]
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CONFIG="${1:-Release}"
SRC="third_party/MotionGloveSDK_cpp"
BUILD_DIR="build/mgsdk_cpp"
INSTALL_DIR="$BUILD_DIR/install"

if [ ! -f "$SRC/CMakeLists.txt" ]; then
    echo "[error] 未找到 $SRC/CMakeLists.txt" >&2
    echo "        请先初始化子模块：git submodule update --init --recursive" >&2
    exit 1
fi

if ! command -v cmake >/dev/null 2>&1; then
    echo "[error] 未找到 cmake，请先安装 CMake" >&2
    exit 1
fi

echo "[1/3] CMake configure ($CONFIG) ..."
cmake -S "$SRC" -B "$BUILD_DIR" -DCMAKE_BUILD_TYPE="$CONFIG" -DBUILD_TESTS=OFF

echo "[2/3] CMake build target MotionGloveSDK ($CONFIG) ..."
cmake --build "$BUILD_DIR" --config "$CONFIG" --target MotionGloveSDK -j "$(nproc 2>/dev/null || echo 4)"

echo "[3/3] CMake install to $INSTALL_DIR ..."
cmake --install "$BUILD_DIR" --config "$CONFIG" --prefix "$INSTALL_DIR"

echo
echo "[done] libMotionGloveSDK.so -> $INSTALL_DIR/lib"
