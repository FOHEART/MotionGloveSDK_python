:; exec sh -c "$(sed -n '/^#__SH__/,$p' "$0" | tr -d '\r')" "$0" "$@" #
@echo off
chcp 65001 >nul
REM ============================================================================
REM  Generate Doxygen HTML documentation and verify the build is warning-free.
REM
REM  This single file runs under BOTH interpreters:
REM    Windows    : scripts\gen_docs.cmd
REM    Linux/macOS: sh scripts/gen_docs.cmd
REM
REM  doxygen 查找顺序：
REM    1. 环境变量 DOXYGEN 指定的可执行文件路径
REM    2. Windows 常见安装位置 D:\autotools\doxygen-1.11.0\doxygen.exe
REM    3. PATH 中的 doxygen
REM
REM  验收标准：doxygen_warnings.log 为 0 字节、退出码 0、docs\html\index.html 生成。
REM ============================================================================
setlocal EnableExtensions

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
pushd "%ROOT%" >nul 2>&1
if errorlevel 1 (
    echo [gen_docs] cannot enter project root: %ROOT%
    exit /b 1
)

if not exist "Doxyfile" (
    echo [gen_docs] Doxyfile not found in %ROOT%
    goto fail
)

set "DOXYGEN_BIN=%DOXYGEN%"
if not defined DOXYGEN_BIN if exist "D:\autotools\doxygen-1.11.0\doxygen.exe" set "DOXYGEN_BIN=D:\autotools\doxygen-1.11.0\doxygen.exe"
if not defined DOXYGEN_BIN (
    for /f "delims=" %%P in ('where doxygen 2^>nul') do if not defined DOXYGEN_BIN set "DOXYGEN_BIN=%%P"
)
if not defined DOXYGEN_BIN (
    echo [gen_docs] doxygen not found. Set DOXYGEN=C:\path\to\doxygen.exe or add it to PATH.
    goto fail
)
if not exist "%DOXYGEN_BIN%" (
    echo [gen_docs] doxygen not found: %DOXYGEN_BIN%
    goto fail
)

if exist "doxygen_warnings.log" del "doxygen_warnings.log"

echo [gen_docs] running %DOXYGEN_BIN% ...
"%DOXYGEN_BIN%" Doxyfile
if errorlevel 1 (
    echo [gen_docs] doxygen FAILED. See doxygen_warnings.log
    goto fail
)

REM doxygen 有告警时退出码仍可能是 0，必须单独按日志大小判定
set "WARN_SIZE=0"
if exist "doxygen_warnings.log" for %%I in ("doxygen_warnings.log") do set "WARN_SIZE=%%~zI"
if not "%WARN_SIZE%"=="0" (
    echo [gen_docs] warnings log is not empty ^(%WARN_SIZE% bytes^). See doxygen_warnings.log
    goto fail
)

if not exist "docs\html\index.html" (
    echo [gen_docs] docs\html\index.html was not generated
    goto fail
)

echo [gen_docs] OK: zero warnings, docs\html\index.html generated.
popd
exit /b 0

:fail
popd
exit /b 1

#__SH__
# ===== POSIX 段（Linux / macOS）=====
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd) || exit 1
cd "$ROOT" || exit 1

if [ ! -f "Doxyfile" ]; then
    echo "[gen_docs] Doxyfile not found in $ROOT" >&2
    exit 1
fi

DOXYGEN_BIN="${DOXYGEN:-}"
if [ -z "$DOXYGEN_BIN" ] && command -v doxygen >/dev/null 2>&1; then
    DOXYGEN_BIN=$(command -v doxygen)
fi
if [ -z "$DOXYGEN_BIN" ]; then
    echo "[gen_docs] doxygen not found. Set DOXYGEN=/path/to/doxygen or add it to PATH." >&2
    exit 1
fi
if [ ! -x "$DOXYGEN_BIN" ]; then
    echo "[gen_docs] doxygen not executable: $DOXYGEN_BIN" >&2
    exit 1
fi

rm -f doxygen_warnings.log

echo "[gen_docs] running $DOXYGEN_BIN ..."
"$DOXYGEN_BIN" Doxyfile || {
    echo "[gen_docs] doxygen FAILED. See doxygen_warnings.log" >&2
    exit 1
}

# doxygen 有告警时退出码仍可能是 0，必须单独按日志大小判定
warn_size=0
if [ -f doxygen_warnings.log ]; then
    warn_size=$(wc -c < doxygen_warnings.log | tr -d ' ')
fi
warn_size=${warn_size:-0}
if [ "$warn_size" -ne 0 ]; then
    echo "[gen_docs] warnings log is not empty ($warn_size bytes). See doxygen_warnings.log" >&2
    exit 1
fi

if [ ! -f docs/html/index.html ]; then
    echo "[gen_docs] docs/html/index.html was not generated" >&2
    exit 1
fi

echo "[gen_docs] OK: zero warnings, docs/html/index.html generated."
exit 0
