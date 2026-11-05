:; exec sh -c "$(sed -n '/^#__SH__/,$p' "$0" | tr -d '\r')" "$0" "$@" #
@echo off
chcp 65001 >nul
REM ============================================================================
REM  Build csv_to_bvh (src\csv_to_bvh.py) with PyInstaller.
REM
REM  This single file runs under BOTH interpreters:
REM    Windows    : scripts\build_csv_to_bvh.bat [--no-bundle-python] [extra pyinstaller args]
REM    Linux/macOS: sh scripts/build_csv_to_bvh.bat [--no-bundle-python] [extra pyinstaller args]
REM
REM  Output layout (identical on both platforms):
REM    dist\csv_to_bvh\csv_to_bvh.exe      (Windows)
REM    dist/csv_to_bvh/csv_to_bvh          (Linux/macOS)
REM
REM  --bundle-python（默认开启）：把 python_embed\<platform> 一并复制到输出目录，
REM  供分发包携带独立解释器；找不到该目录时只提示、不中断。
REM ============================================================================
setlocal EnableExtensions EnableDelayedExpansion

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
pushd "%ROOT%" >nul 2>&1
if errorlevel 1 (
    echo [error] 无法进入工程目录：%ROOT%
    exit /b 1
)

set "SPEC=%ROOT%\csv_to_bvh.spec"
set "OUTDIR=%ROOT%\dist\csv_to_bvh"
set "PYTHONPATH=%ROOT%\libs;%ROOT%\src;%PYTHONPATH%"

if not exist "%SPEC%" (
    echo [error] 未找到 %SPEC%
    goto fail
)

where python >nul 2>nul
if errorlevel 1 (
    echo [error] 未找到 python，请先安装 Python 3.10+ 并加入 PATH
    goto fail
)

REM 解析参数：--no-bundle-python 由本脚本消费，其余原样转发给 PyInstaller
set "BUNDLE_PY=1"
set "FORWARDED_ARGS="
for %%A in (%*) do (
    if /I "%%~A"=="--no-bundle-python" (
        set "BUNDLE_PY=0"
    ) else (
        set "FORWARDED_ARGS=!FORWARDED_ARGS! %%~A"
    )
)

echo [1/2] Building csv_to_bvh with PyInstaller...
python -m PyInstaller --noconfirm --clean "%SPEC%" !FORWARDED_ARGS!
if errorlevel 1 (
    echo [error] PyInstaller 打包失败
    goto fail
)

echo.
echo [2/2] 整理产物到 dist\csv_to_bvh\ ...
if exist "%OUTDIR%" rd /s /q "%OUTDIR%"
mkdir "%OUTDIR%" >nul 2>&1
if exist "%ROOT%\dist\csv_to_bvh.exe" (
    move /Y "%ROOT%\dist\csv_to_bvh.exe" "%OUTDIR%\" >nul
) else (
    echo [WARN] 未在 dist\ 下找到 csv_to_bvh.exe，跳过产物整理。
    goto done
)

if "%BUNDLE_PY%"=="1" (
    if exist "%ROOT%\python_embed\windows" (
        echo     Bundling embeddable Python from python_embed\windows
        xcopy /e /i /y /q "%ROOT%\python_embed\windows" "%OUTDIR%\python_embed\windows" >nul
        if errorlevel 1 echo [WARN] 复制 python_embed\windows 失败，已跳过。
    ) else (
        echo [WARN] --bundle-python 需要 python_embed\windows，未找到，已跳过。
    )
)

:done
echo.
echo [done] dist\csv_to_bvh\csv_to_bvh.exe
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

export PYTHONPATH="$ROOT/libs:$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
SPEC="$ROOT/csv_to_bvh.spec"
OUTDIR="dist/csv_to_bvh"

if [ ! -f "$SPEC" ]; then
    echo "[error] 未找到 $SPEC" >&2
    exit 1
fi

if [ -n "${PYTHON:-}" ]; then
    PY="$PYTHON"
elif command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "[error] 未找到 python3 / python，请先安装 Python 3.10+" >&2
    exit 1
fi

# 解析参数：--no-bundle-python 由本脚本消费，其余原样转发给 PyInstaller
BUNDLE_PY=1
FORWARDED=""
for a in "$@"; do
    if [ "$a" = "--no-bundle-python" ]; then
        BUNDLE_PY=0
        continue
    fi
    esc=$(printf '%s' "$a" | sed "s/'/'\\\\''/g")
    FORWARDED="$FORWARDED '$esc'"
done
eval "set -- $FORWARDED"

echo "[1/2] Building csv_to_bvh with PyInstaller..."
"$PY" -m PyInstaller --noconfirm --clean "$SPEC" "$@" || {
    echo "[error] PyInstaller 打包失败" >&2
    exit 1
}

echo ""
echo "[2/2] 整理产物到 $OUTDIR/ ..."
rm -rf "dist/csv_to_bvh.tmp"
mkdir -p "dist/csv_to_bvh.tmp"
bin=""
for cand in "dist/csv_to_bvh" "dist/csv_to_bvh.exe"; do
    if [ -f "$cand" ]; then bin="$cand"; fi
done
if [ -n "$bin" ]; then
    mv -f "$bin" "dist/csv_to_bvh.tmp/"
fi
rm -rf "$OUTDIR"
mv "dist/csv_to_bvh.tmp" "$OUTDIR"
if [ -z "$bin" ]; then
    echo "[WARN] 未在 dist/ 下找到 csv_to_bvh 可执行文件，跳过产物整理。"
    echo "[done] 见 $OUTDIR/"
    exit 0
fi

if [ "$BUNDLE_PY" -eq 1 ]; then
    if [ -d "python_embed/linux" ]; then
        echo "    Bundling embeddable Python from python_embed/linux"
        mkdir -p "$OUTDIR/python_embed"
        cp -R "python_embed/linux" "$OUTDIR/python_embed/" || echo "[WARN] 复制 python_embed/linux 失败，已跳过。"
    else
        echo "[WARN] --bundle-python 需要 python_embed/linux，未找到，已跳过。"
    fi
fi

echo ""
echo "[done] $OUTDIR/csv_to_bvh"
exit 0
