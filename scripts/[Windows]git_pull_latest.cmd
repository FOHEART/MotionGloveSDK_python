@echo off
setlocal
set ROOT_DIR=%~dp0..

echo [fetch_latest] Fetching latest from origin...
cd /d "%ROOT_DIR%"

git fetch origin
if %errorlevel% neq 0 (
    echo [ERROR] git fetch failed.
    pause
    exit /b %errorlevel%
)

git pull origin main
if %errorlevel% neq 0 (
    echo [ERROR] git pull failed.
    pause
    exit /b %errorlevel%
)

echo [fetch_latest] Syncing submodules (third_party/MotionGloveSDK_cpp)...
git submodule update --init --recursive
if %errorlevel% neq 0 (
    echo [ERROR] git submodule update failed.
    pause
    exit /b %errorlevel%
)

echo.
echo [fetch_latest] Rebuilding native library...
call "%ROOT_DIR%\scripts\[Windows]build_mgsdk_cpp.cmd"
if %errorlevel% neq 0 (
    echo [ERROR] native library build failed.
    pause
    exit /b %errorlevel%
)

echo.
echo [fetch_latest] Done. Current status:
git log --oneline -5

echo.
pause
endlocal
