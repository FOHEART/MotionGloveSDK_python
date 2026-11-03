:; exec sh -c "$(sed -n '/^#__SH__/,$p' "$0" | tr -d '\r')" "$0" "$@" #
@echo off
chcp 65001 >nul
REM ============================================================================
REM  Update and compile Qt translations (lupdate -> lrelease).
REM
REM  This single file runs under BOTH interpreters:
REM    Windows    : scripts\update_translations.cmd
REM    Linux/macOS: sh scripts/update_translations.cmd
REM
REM  lupdate / lrelease come from libs\PySide6（由 setup_python_libs.cmd 安装）。
REM  Linux 上若 libs/PySide6 下没有可执行文件，则回退到 PATH 里的
REM  lupdate / lrelease 或 pyside6-lupdate / pyside6-lrelease。
REM ============================================================================
setlocal EnableExtensions EnableDelayedExpansion

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
pushd "%ROOT%" >nul 2>&1
if errorlevel 1 (
    echo [error] 无法进入工程目录：%ROOT%
    exit /b 1
)

set "LUPDATE=%ROOT%\libs\PySide6\lupdate.exe"
set "LRELEASE=%ROOT%\libs\PySide6\lrelease.exe"

if not exist "%LUPDATE%" (
    echo ERROR: lupdate not found at %LUPDATE%
    goto fail2
)
if not exist "%LRELEASE%" (
    echo ERROR: lrelease not found at %LRELEASE%
    goto fail3
)

set "SOURCES=motionGloveSDK_example3_3dView.py src\boot_mode_dialog.py ui\left_panel.ui ui\csv_import_panel.ui ui\left_panel_widget.py ui\draw_config_widget.py ui\csv_import_widget.py ui\oss_licenses_dialog.py"

echo Running lupdate to extract strings into .ts files...
for %%F in (translations\*.ts) do (
    echo  - Updating %%F
    "%LUPDATE%" !SOURCES! -no-obsolete -ts "%%F"
    if errorlevel 1 echo WARNING: lupdate failed for %%F
)

echo Compiling .ts -^> .qm with lrelease...
for %%F in (translations\*.ts) do (
    set "BASENAME=%%~nF"
    echo  - Compiling %%F -^> translations\!BASENAME!.qm
    "%LRELEASE%" "%%F" -qm "translations\!BASENAME!.qm"
    if errorlevel 1 echo WARNING: lrelease failed for %%F
)

echo Done. Generated .qm files are in translations\
popd
exit /b 0

:fail2
popd
exit /b 2

:fail3
popd
exit /b 3

#__SH__
# ===== POSIX 段（Linux / macOS）=====
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd) || exit 1
cd "$ROOT" || exit 1

pick_tool() {
    # $1 = libs 下的工具名（lupdate / lrelease），回退到 PATH
    tool="$ROOT/libs/PySide6/$1"
    if [ -x "$tool" ]; then
        printf '%s\n' "$tool"
        return 0
    fi
    if command -v "$1" >/dev/null 2>&1; then
        command -v "$1"
        return 0
    fi
    if command -v "pyside6-$1" >/dev/null 2>&1; then
        command -v "pyside6-$1"
        return 0
    fi
    return 1
}

LUPDATE=$(pick_tool lupdate) || {
    echo "[ERROR] 未找到 lupdate（期望 $ROOT/libs/PySide6/lupdate 或 PATH 中的 lupdate）。" >&2
    echo "        请先安装依赖：sh scripts/setup_python_libs.cmd" >&2
    exit 2
}
LRELEASE=$(pick_tool lrelease) || {
    echo "[ERROR] 未找到 lrelease（期望 $ROOT/libs/PySide6/lrelease 或 PATH 中的 lrelease）。" >&2
    echo "        请先安装依赖：sh scripts/setup_python_libs.cmd" >&2
    exit 3
}

# 源码 / UI 文件清单（与 Windows 段保持一致；路径不含空格，故直接展开）
SOURCES="motionGloveSDK_example3_3dView.py src/boot_mode_dialog.py ui/left_panel.ui ui/csv_import_panel.ui ui/left_panel_widget.py ui/draw_config_widget.py ui/csv_import_widget.py ui/oss_licenses_dialog.py"

echo "Running lupdate to extract strings into .ts files..."
for ts in translations/*.ts; do
    [ -f "$ts" ] || continue
    echo " - Updating $ts"
    # shellcheck disable=SC2086
    "$LUPDATE" $SOURCES -no-obsolete -ts "$ts" || echo "WARNING: lupdate failed for $ts"
done

echo "Compiling .ts -> .qm with lrelease..."
for ts in translations/*.ts; do
    [ -f "$ts" ] || continue
    base=$(basename "$ts" .ts)
    echo " - Compiling $ts -> translations/$base.qm"
    "$LRELEASE" "$ts" -qm "translations/$base.qm" || echo "WARNING: lrelease failed for $ts"
done

echo "Done. Generated .qm files are in translations/"
