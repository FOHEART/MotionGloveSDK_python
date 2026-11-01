@echo off
REM ============================================================================
REM  Build the C++ MotionGloveSDK (third_party/MotionGloveSDK_cpp) into
REM  build\mgsdk_cpp\install\{bin,lib} so that src\native can load it.
REM
REM  Usage:
REM    scripts\[Windows]build_mgsdk_cpp.cmd [Release|Debug]
REM ============================================================================
setlocal

set "ROOT=%~dp0.."
pushd "%ROOT%"

set "CONFIG=%~1"
if "%CONFIG%"=="" set "CONFIG=Release"

set "SRC=third_party\MotionGloveSDK_cpp"
set "BUILD_DIR=build\mgsdk_cpp"
set "INSTALL_DIR=%BUILD_DIR%\install"

if not exist "%SRC%\CMakeLists.txt" (
    echo [error] 未找到 %SRC%\CMakeLists.txt
    echo         请先初始化子模块：git submodule update --init --recursive
    popd
    exit /b 1
)

where cmake >nul 2>nul
if errorlevel 1 (
    echo [error] 未找到 cmake，请安装 CMake 并加入 PATH
    popd
    exit /b 1
)

echo [1/3] CMake configure (%CONFIG%) ...
cmake -S "%SRC%" -B "%BUILD_DIR%" -A x64 -DCMAKE_CONFIGURATION_TYPES="Debug;Release" -DBUILD_TESTS=OFF
if errorlevel 1 (
    echo [error] CMake configure 失败
    popd
    exit /b 1
)

echo [2/3] CMake build target MotionGloveSDK (%CONFIG%) ...
cmake --build "%BUILD_DIR%" --config "%CONFIG%" --target MotionGloveSDK
if errorlevel 1 (
    echo [error] 编译失败
    popd
    exit /b 1
)

echo [3/3] CMake install to %INSTALL_DIR% ...
cmake --install "%BUILD_DIR%" --config "%CONFIG%" --prefix "%INSTALL_DIR%"
if errorlevel 1 (
    echo [error] install 失败
    popd
    exit /b 1
)

echo.
echo [done] MotionGloveSDK.dll -^> %INSTALL_DIR%\bin
popd
exit /b 0
