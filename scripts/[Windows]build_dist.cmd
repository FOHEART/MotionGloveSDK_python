@echo off
chcp 65001 >nul

set ROOT_DIR=%~dp0..
cd /d "%ROOT_DIR%"

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
    --onedir ^
    %CONSOLE_FLAG% ^
    --name "MotionGlove3DViewer" ^
    --distpath "%ROOT_DIR%\dist" ^
    --workpath "%ROOT_DIR%\build" ^
    --specpath "%ROOT_DIR%\build" ^
    --paths "%ROOT_DIR%\libs" ^
    --paths "%ROOT_DIR%\src" ^
    --paths "%ROOT_DIR%\python_draw3d" ^
    --paths "%ROOT_DIR%\ui" ^
    --add-data "%ROOT_DIR%\fonts;fonts" ^
    --add-data "%ROOT_DIR%\ui\left_panel.ui;ui" ^
    --hidden-import vtkmodules.all ^
    --hidden-import vtkmodules.qt.QVTKRenderWindowInteractor ^
    --hidden-import PySide6.QtWidgets ^
    --hidden-import PySide6.QtCore ^
    --hidden-import PySide6.QtGui ^
    --collect-all vtk ^
    --collect-all vtkmodules ^
    --collect-all PySide6 ^
    "%ROOT_DIR%\motionGloveSDK_example3_3dView.py"

if %errorlevel% neq 0 (
    echo [build] PyInstaller failed, exit code: %errorlevel%
    pause
    exit /b %errorlevel%
)

echo.
echo [build] Done. Output: %ROOT_DIR%\dist\MotionGlove3DViewer\
exit /b 0
