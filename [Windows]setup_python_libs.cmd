@echo off
chcp 65001 >nul

echo [1/2] Installing runtime dependencies to libs\ ...
REM 以下版本针对 Python 3.10 适配（部分包的更高版本需要 Python 3.11+）
REM numpy 2.4.x、contourpy 1.3.3+ 等需 Python 3.11+
pip install vtk==9.6.0 numpy==2.2.6 matplotlib==3.10.8 Pillow==12.1.1 ^
    pyparsing==3.3.2 python-dateutil==2.9.0.post0 packaging==26.0 ^
    fonttools==4.62.0 contourpy==1.3.2 cycler==0.12.1 kiwisolver==1.4.9 six==1.17.0 ^
    --target libs
if %errorlevel% neq 0 (
    echo Runtime dependency installation failed, exit code: %errorlevel%
    pause
    exit /b %errorlevel%
)

echo.
echo [2/2] Installing dev tools to system Python (pyinstaller, pybind11)...
pip install pyinstaller==6.19.0 pybind11==2.13.6
if %errorlevel% neq 0 (
    echo Dev tools installation failed, exit code: %errorlevel%
    pause
    exit /b %errorlevel%
)

echo.
echo Done.
exit /b 0
