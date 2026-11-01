@echo off
rem gen_docs.bat - Generate Doxygen HTML documentation and verify zero warnings.
rem Usage: gen_docs.bat   (run from the repository root)

setlocal
set DOXYGEN=D:\autotools\doxygen-1.11.0\doxygen.exe

if not exist "%DOXYGEN%" (
    echo [gen_docs] doxygen not found: %DOXYGEN%
    exit /b 1
)

if exist doxygen_warnings.log del doxygen_warnings.log

"%DOXYGEN%" Doxyfile
if errorlevel 1 (
    echo [gen_docs] doxygen FAILED. See doxygen_warnings.log
    exit /b 1
)

for %%I in (doxygen_warnings.log) do set SIZE=%%~zI
if not "%SIZE%"=="0" (
    echo [gen_docs] warnings log is not empty (%SIZE% bytes^). See doxygen_warnings.log
    exit /b 1
)

echo [gen_docs] OK: zero warnings, docs\html\index.html generated.
exit /b 0
