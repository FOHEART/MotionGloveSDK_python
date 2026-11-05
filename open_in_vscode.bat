:; exec sh -c "$(sed -n '/^#__SH__/,$p' "$0" | tr -d '\r')" "$0" "$@" #
@echo off
chcp 65001 >nul
REM ============================================================================
REM  Open the project root in VSCode.
REM
REM  This single file runs under BOTH interpreters:
REM    Windows    : open_in_vscode.bat
REM    Linux/macOS: sh open_in_vscode.bat
REM ============================================================================
setlocal EnableExtensions

for %%I in ("%~dp0.") do set "ROOT_DIR=%%~fI"

where code >nul 2>nul
if errorlevel 1 (
    echo [ERROR] 未找到 code 命令。安装 VSCode 时请勾选 "Add to PATH"，
    echo         或把 "...\Microsoft VS Code\bin" 加入 PATH 后重试。
    exit /b 1
)

code "%ROOT_DIR%"
exit /b %errorlevel%

#__SH__
# ===== POSIX 段（Linux / macOS）=====
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1

if ! command -v code >/dev/null 2>&1; then
    echo "[ERROR] 未找到 code 命令。请先安装 VSCode 并在命令面板执行" >&2
    echo '        "Shell Command: Install '\''code'\'' command in PATH"。' >&2
    exit 1
fi

code "$ROOT_DIR"
