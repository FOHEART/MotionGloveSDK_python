@echo off
rem Update and compile Qt translations (lupdate -> lrelease)
rem Usage: double-click or run from repository root: scripts\update_translations.bat
setlocal enableextensions enabledelayedexpansion
pushd "%~dp0.."

set LUPDATE=%~dp0..\libs\PySide6\lupdate.exe
set LRELEASE=%~dp0..\libs\PySide6\lrelease.exe

if not exist "%LUPDATE%" (
  echo ERROR: lupdate not found at %LUPDATE%
  popd
  exit /b 2
)
if not exist "%LRELEASE%" (
  echo ERROR: lrelease not found at %LRELEASE%
  popd
  exit /b 3
)

echo Running lupdate to extract strings into .ts files...
set SOURCES="motionGloveSDK_example3_3dView.py" "src\boot_mode_dialog.py" "ui\left_panel.ui" "ui\csv_import_panel.ui" "ui\left_panel_widget.py" "ui\draw_config_widget.py" "ui\csv_import_widget.py" "ui\oss_licenses_dialog.py"
for %%F in (translations\*.ts) do (
  echo  - Updating %%F
  "%LUPDATE%" %SOURCES% -no-obsolete -ts "%%F"
  if errorlevel 1 (
    echo WARNING: lupdate failed for %%F
  )
)

echo Compiling .ts -> .qm with lrelease...
for %%F in (translations\*.ts) do (
  set "BASENAME=%%~nF"
  echo  - Compiling %%F -> translations\!BASENAME!.qm
  "%LRELEASE%" "%%F" -qm "translations\!BASENAME!.qm"
  if errorlevel 1 (
    echo WARNING: lrelease failed for %%F
  )
)

echo Done. Generated .qm files are in translations\
popd
endlocal
exit /b 0
