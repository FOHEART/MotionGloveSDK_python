:; exec sh -c "$(sed -n '/^#__SH__/,$p' "$0" | tr -d '\r')" "$0" "$@" #
@echo off
chcp 65001 >nul
REM ============================================================================
REM  Install Python dependencies.
REM    step 1: runtime deps (vtk / numpy / matplotlib / Pillow / pyside6 ...) -> libs\
REM    step 2: dev tools (pyinstaller / pybind11) -> system Python
REM
REM  This single file runs under BOTH interpreters:
REM    Windows   : scripts\setup_python_libs.bat
REM    Linux/macOS: sh scripts/setup_python_libs.bat
REM ============================================================================
setlocal EnableExtensions

for %%I in ("%~dp0..") do set "ROOT_DIR=%%~fI"
set "LIBS_DIR=%ROOT_DIR%\libs"

echo [1/2] Installing runtime dependencies to libs\ ...
REM 以下版本针对 Python 3.10 适配（部分包的更高版本需要 Python 3.11+）
REM numpy 2.x 与 pyside6 6.11.x 必须成对使用：pyside6 6.5.x 的 shiboken6 是按
REM NumPy 1.x 编译的，且与 VTK 9.6 组合时进程退出会崩溃（0xC0000005）。
pip install vtk==9.6.0 numpy==2.2.6 matplotlib==3.10.8 Pillow==12.1.1 ^
    pyparsing==3.3.2 python-dateutil==2.9.0.post0 packaging==26.0 ^
    fonttools==4.62.0 contourpy==1.3.2 cycler==0.12.1 kiwisolver==1.4.9 six==1.17.0 ^
    pyside6==6.11.0 ^
    --target "%LIBS_DIR%"
if errorlevel 1 (
    echo [error] Runtime dependency installation failed.
    exit /b 1
)

echo.
echo [2/2] Installing dev tools to system Python (pyinstaller, pybind11)...
pip install pyinstaller==6.19.0 pybind11==2.13.6
if errorlevel 1 (
    echo [error] Dev tools installation failed.
    exit /b 1
)

echo.
echo [done] libs\ = %LIBS_DIR%
exit /b 0

#__SH__
# ===== POSIX 段（Linux / macOS）=====
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd) || exit 1
LIBS_DIR="$ROOT_DIR/libs"

if [ -n "${PYTHON:-}" ]; then
    PY="$PYTHON"
elif command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "[error] 未找到 python3 / python，请先安装 Python 3.10+。" >&2
    exit 1
fi
echo "[info] 使用 $PY（$("$PY" --version 2>&1)）"

echo "[1/2] 安装运行时依赖到 libs/ ..."
# 以下版本针对 Python 3.10 适配（部分包的更高版本需要 Python 3.11+）
# numpy 2.x 与 pyside6 6.11.x 必须成对使用：pyside6 6.5.x 的 shiboken6 是按
# NumPy 1.x 编译的，且与 VTK 9.6 组合时进程退出会崩溃。
"$PY" -m pip install \
    vtk==9.6.0 numpy==2.2.6 matplotlib==3.10.8 Pillow==12.1.1 \
    pyparsing==3.3.2 python-dateutil==2.9.0.post0 packaging==26.0 \
    fonttools==4.62.0 contourpy==1.3.2 cycler==0.12.1 kiwisolver==1.4.9 six==1.17.0 \
    pyside6==6.11.0 \
    --target "$LIBS_DIR" || {
    echo "[error] 运行时依赖安装失败。" >&2
    exit 1
}

echo ""
echo "[2/2] 安装开发工具到系统 Python（pyinstaller、pybind11）..."
"$PY" -m pip install pyinstaller==6.19.0 pybind11==2.13.6 || {
    echo "[error] 开发工具安装失败。" >&2
    exit 1
}

echo ""
echo "[done] libs/ = $LIBS_DIR"
exit 0
