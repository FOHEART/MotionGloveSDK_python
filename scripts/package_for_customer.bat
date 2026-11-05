:; exec sh -c "$(sed -n '/^#__SH__/,$p' "$0" | tr -d '\r')" "$0" "$@" #
@echo off
chcp 65001 >nul
REM ============================================================================
REM  Package the project into a customer-facing zip (no git metadata, no git
REM  helper scripts). All the logic lives in scripts\lib\package_for_customer.ps1.
REM
REM  This single file runs under BOTH interpreters:
REM    Windows    : scripts\package_for_customer.bat [-Version x.y.z] [-KeepStaging]
REM    Linux/macOS: sh scripts/package_for_customer.bat [-Version x.y.z] [-KeepStaging]
REM                 （Linux/macOS 需要 PowerShell 7：pwsh）
REM ============================================================================
setlocal EnableExtensions

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "SCRIPT=%ROOT%\scripts\lib\package_for_customer.ps1"

if not exist "%SCRIPT%" (
    echo [error] 未找到 %SCRIPT%
    exit /b 1
)

where powershell >nul 2>nul
if errorlevel 1 (
    echo [error] 未找到 powershell，请安装 Windows PowerShell 或 PowerShell 7
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" %*
exit /b %errorlevel%

#__SH__
# ===== POSIX 段（Linux / macOS）=====
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd) || exit 1
PS_SCRIPT="$SCRIPT_DIR/lib/package_for_customer.ps1"

if [ ! -f "$PS_SCRIPT" ]; then
    echo "[error] 未找到 $PS_SCRIPT" >&2
    exit 1
fi

PS=""
for cand in pwsh pwsh-lts powershell; do
    if command -v "$cand" >/dev/null 2>&1; then
        PS=$(command -v "$cand")
        break
    fi
done
if [ -z "$PS" ]; then
    echo "[error] 未找到 PowerShell，无法打包。" >&2
    echo "        Linux/macOS 请先安装 PowerShell 7（pwsh）：https://aka.ms/powershell" >&2
    exit 1
fi

cd "$ROOT" || exit 1
"$PS" -NoProfile -File "$PS_SCRIPT" "$@"
exit $?
