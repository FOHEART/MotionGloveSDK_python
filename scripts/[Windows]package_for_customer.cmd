@echo off
REM ============================================================================
REM  Package the project into a customer-facing zip (no git metadata, no git
REM  helper scripts). Logic lives in scripts\package_for_customer.ps1.
REM
REM  Usage:
REM    scripts\[Windows]package_for_customer.cmd [ps1 args...]
REM  Examples:
REM    scripts\[Windows]package_for_customer.cmd
REM    scripts\[Windows]package_for_customer.cmd -Version 0.2.2 -KeepStaging
REM ============================================================================
setlocal

set "SCRIPT=%~dp0package_for_customer.ps1"
if not exist "%SCRIPT%" (
    echo [error] 未找到 %SCRIPT%
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" %*
exit /b %errorlevel%
