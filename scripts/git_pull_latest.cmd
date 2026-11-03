:; exec sh -c "$(sed -n '/^#__SH__/,$p' "$0" | tr -d '\r')" "$0" "$@" #
@echo off
chcp 65001 >nul
REM ============================================================================
REM  Pull the latest code from origin, sync submodules, rebuild the native SDK.
REM
REM  This single file runs under BOTH interpreters:
REM    Windows    : scripts\git_pull_latest.cmd
REM    Linux/macOS: sh scripts/git_pull_latest.cmd
REM ============================================================================
setlocal EnableExtensions

for %%I in ("%~dp0..") do set "ROOT_DIR=%%~fI"
cd /d "%ROOT_DIR%"
if errorlevel 1 (
    echo [ERROR] 无法进入工程目录：%ROOT_DIR%
    exit /b 1
)

echo [fetch_latest] Fetching latest from origin...
git fetch origin
if errorlevel 1 (
    echo [ERROR] git fetch failed.
    exit /b 1
)

git pull origin main
if errorlevel 1 (
    echo [ERROR] git pull failed.
    exit /b 1
)

echo [fetch_latest] Syncing submodules (third_party/MotionGloveSDK_cpp)...
git submodule update --init --recursive
if errorlevel 1 (
    echo [ERROR] git submodule update failed.
    exit /b 1
)

echo.
echo [fetch_latest] Rebuilding native library...
call "%ROOT_DIR%\scripts\build_mgsdk_cpp.cmd"
if errorlevel 1 (
    echo [ERROR] native library build failed.
    exit /b 1
)

echo.
echo [fetch_latest] Done. Current status:
git --no-pager log --oneline -5
exit /b 0

#__SH__
# ===== POSIX 段（Linux / macOS）=====
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd) || exit 1
cd "$ROOT_DIR" || exit 1

echo "[fetch_latest] Fetching latest from origin..."
git fetch origin || { echo "[ERROR] git fetch failed."; exit 1; }

git pull origin main || { echo "[ERROR] git pull failed."; exit 1; }

echo "[fetch_latest] Syncing submodules (third_party/MotionGloveSDK_cpp)..."
git submodule update --init --recursive || { echo "[ERROR] git submodule update failed."; exit 1; }

echo "[fetch_latest] Rebuilding native library..."
sh "$SCRIPT_DIR/build_mgsdk_cpp.cmd" || { echo "[ERROR] native library build failed."; exit 1; }

echo ""
echo "[fetch_latest] Done. Current status:"
git --no-pager log --oneline -5
