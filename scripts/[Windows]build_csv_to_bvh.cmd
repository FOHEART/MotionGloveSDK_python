@echo off
REM Build csv_to_bvh.exe using PyInstaller
REM Usage: scripts\[Windows]build_csv_to_bvh.cmd [additional pyinstaller args]
setlocal enabledelayedexpansion

cd /d "%~dp0\.."

set PYTHONPATH=%CD%\libs;%CD%\src;%PYTHONPATH%

echo Building csv_to_bvh with PyInstaller...

REM Parse args and support --bundle-python to include an embeddable Python folder
set "FORWARDED_ARGS="
REM Bundle Python by default; use --no-bundle-python to disable
set "BUNDLE_PY=1"
for %%A in (%*) do (
  if /I "%%~A"=="--no-bundle-python" (
    set "BUNDLE_PY=0"
  ) else (
    set "FORWARDED_ARGS=!FORWARDED_ARGS! %%~A"
  )
)

set "ADD_DATA_ARGS="
if "%BUNDLE_PY%"=="1" (
  if exist "%~dp0\..\python_embed\windows" (
    set "ADD_DATA_ARGS=--add-data ""%~dp0\..\python_embed\windows;python_embed\windows"""
    echo Bundling embeddable Python from python_embed\windows
  ) else (
    echo Warning: --bundle-python requested but python_embed\windows not found.
  )
)

python -m PyInstaller --noconfirm --clean "%~dp0\..\csv_to_bvh.spec" %FORWARDED_ARGS%

if %ERRORLEVEL% neq 0 (
  echo Build failed with error %ERRORLEVEL%.
  exit /b %ERRORLEVEL%
)

REM Ensure output placed under dist\csv_to_bvh folder
set "ROOT=%~dp0\.."
if exist "%ROOT%\dist\csv_to_bvh" (
  rmdir /s /q "%ROOT%\dist\csv_to_bvh"
)
mkdir "%ROOT%\dist\csv_to_bvh" >nul 2>&1 || (
  echo Failed to create target directory "%ROOT%\dist\csv_to_bvh".
)

if exist "%ROOT%\dist\csv_to_bvh.exe" (
  move /Y "%ROOT%\dist\csv_to_bvh.exe" "%ROOT%\dist\csv_to_bvh\" >nul
) else if exist "%ROOT%\dist\csv_to_bvh\csv_to_bvh.exe" (
  rem already in place
) else (
  echo Warning: built executable not found in dist\
)

echo Build finished. See "dist\csv_to_bvh\csv_to_bvh.exe".
endlocal
exit /b 0
