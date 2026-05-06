@echo off
chcp 65001 >nul

set ROOT_DIR=%~dp0..
cd /d "%ROOT_DIR%"

set PYTHONPATH=%ROOT_DIR%\libs;%ROOT_DIR%\src;%PYTHONPATH%

REM Control console window visibility via argument.
REM Usage: build_dist.cmd [--console]
REM Default: no console window (--noconsole)
set CONSOLE_FLAG=--noconsole
if /i "%~1"=="--console" set CONSOLE_FLAG=--console

echo [build] Packaging motionGloveSDK_example3_3dView with PyInstaller...
echo [build] ROOT_DIR = %ROOT_DIR%
echo [build] Console window: %CONSOLE_FLAG%

pyinstaller ^
    --noconfirm ^
    --clean ^
    --distpath "%ROOT_DIR%\dist" ^
    --workpath "%ROOT_DIR%\build" ^
    "%ROOT_DIR%\MotionGlove3DViewer.spec"

if %errorlevel% neq 0 (
    echo [build] PyInstaller failed, exit code: %errorlevel%
    pause
    exit /b %errorlevel%
)

echo.
echo [build] Done. Output: %ROOT_DIR%\dist\MotionGlove3DViewer\
exit /b 0
