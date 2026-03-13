@echo off
chcp 65001 >nul

echo [1/2] Installing runtime dependencies to libs\ ...
pip install vtk==9.6.0 numpy==2.4.2 matplotlib==3.10.8 Pillow==12.1.1 ^
    pyparsing==3.3.2 python-dateutil==2.9.0.post0 packaging==26.0 ^
    fonttools==4.61.1 contourpy==1.3.3 cycler==0.12.1 kiwisolver==1.4.9 six==1.17.0 ^
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
