:; exec sh -c "$(sed -n '/^#__SH__/,$p' "$0" | tr -d '\r')" "$0" "$@" #
@echo off
chcp 65001 >nul
REM ============================================================================
REM  Build the C++ MotionGloveSDK (third_party/MotionGloveSDK_cpp) into
REM  build/mgsdk_cpp/install/{bin,lib} so that src/native can load it.
REM
REM  This single file runs under BOTH interpreters:
REM    Windows    : scripts\build_mgsdk_cpp.bat [Release|Debug]
REM    Linux/macOS: sh scripts/build_mgsdk_cpp.bat [Release|Debug]
REM ============================================================================
setlocal EnableExtensions

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
pushd "%ROOT%" >nul 2>&1
if errorlevel 1 (
    echo [error] 无法进入工程目录：%ROOT%
    exit /b 1
)

set "CONFIG=%~1"
if "%CONFIG%"=="" set "CONFIG=Release"

set "SRC=third_party\MotionGloveSDK_cpp"
set "BUILD_DIR=build\mgsdk_cpp"
set "INSTALL_DIR=%BUILD_DIR%\install"

if not exist "%SRC%\CMakeLists.txt" (
    echo [error] 未找到 %SRC%\CMakeLists.txt
    echo         请先初始化子模块：git submodule update --init --recursive
    goto fail
)

where cmake >nul 2>nul
if errorlevel 1 (
    echo [error] 未找到 cmake，请安装 CMake 并加入 PATH
    goto fail
)

echo [1/3] CMake configure (%CONFIG%) ...
cmake -S "%SRC%" -B "%BUILD_DIR%" -A x64 -DCMAKE_CONFIGURATION_TYPES="Debug;Release" -DBUILD_TESTS=OFF
if errorlevel 1 (
    echo [error] CMake configure 失败
    goto fail
)

echo [2/3] CMake build target MotionGloveSDK (%CONFIG%) ...
cmake --build "%BUILD_DIR%" --config "%CONFIG%" --target MotionGloveSDK
if errorlevel 1 (
    echo [error] 编译失败
    goto fail
)

echo [3/3] CMake install to %INSTALL_DIR% ...
cmake --install "%BUILD_DIR%" --config "%CONFIG%" --prefix "%INSTALL_DIR%"
if errorlevel 1 (
    echo [error] install 失败
    goto fail
)

echo.
echo [done] MotionGloveSDK.dll -^> %INSTALL_DIR%\bin
popd
exit /b 0

:fail
popd
exit /b 1

#__SH__
# ===== POSIX 段（Linux / macOS）=====
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd) || exit 1
cd "$ROOT" || exit 1

CONFIG=${1:-Release}
case "$CONFIG" in
    [Dd]ebug)   CONFIG=Debug ;;
    [Rr]elease) CONFIG=Release ;;
    *)          echo "[WARN] 未知配置参数：$CONFIG，按 Release 处理。" ;;
esac
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

JOBS=$( (command -v nproc >/dev/null 2>&1 && nproc) || echo 4 )

echo "[1/3] CMake configure ($CONFIG) ..."
cmake -S "$SRC" -B "$BUILD_DIR" -DCMAKE_BUILD_TYPE="$CONFIG" -DBUILD_TESTS=OFF || {
    echo "[error] CMake configure 失败" >&2
    exit 1
}

echo "[2/3] CMake build target MotionGloveSDK ($CONFIG) ..."
cmake --build "$BUILD_DIR" --config "$CONFIG" --target MotionGloveSDK -j"$JOBS" || {
    echo "[error] 编译失败" >&2
    exit 1
}

echo "[3/3] CMake install to $INSTALL_DIR ..."
cmake --install "$BUILD_DIR" --config "$CONFIG" --prefix "$INSTALL_DIR" || {
    echo "[error] install 失败" >&2
    exit 1
}

echo ""
echo "[done] libMotionGloveSDK.so -> $INSTALL_DIR/lib"
