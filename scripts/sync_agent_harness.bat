:; exec sh -c "$(sed -n '/^#__SH__/,$p' "$0" | tr -d '\r')" "$0" "$@" #
@echo off
chcp 65001 >nul
REM ============================================================================
REM  Sync agent-harness + the single root SKILL.md into a dist/install folder.
REM  Usage: scripts\sync_agent_harness.bat [target-dir]
REM  This single file runs under BOTH interpreters:
REM    Windows   : scripts\sync_agent_harness.bat
REM    Linux/macOS: sh scripts/sync_agent_harness.bat
REM ============================================================================
setlocal EnableExtensions

for %%I in ("%~dp0..") do set "ROOT_DIR=%%~fI"
set "DIST_DIR=%ROOT_DIR%\dist\MotionGlove3DViewer"
if not "%~1"=="" set "DIST_DIR=%~1"

python "%ROOT_DIR%\scripts\lib\sync_agent_harness.py" --dist "%DIST_DIR%"
if errorlevel 1 (
    echo [error] agent-harness sync failed.
    exit /b 1
)
echo [done] agent-harness and SKILL.md are in %DIST_DIR%
exit /b 0

#__SH__
# ===== POSIX 段（Linux / macOS）=====
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd) || exit 1
PY=python3
command -v "$PY" >/dev/null 2>&1 || PY=python
DIST=${1:-"$ROOT/dist/MotionGlove3DViewer"}
"$PY" "$ROOT/scripts/lib/sync_agent_harness.py" --dist "$DIST" || {
    echo "[error] agent-harness sync failed." >&2
    exit 1
}
echo "[done] agent-harness and SKILL.md are in $DIST"
exit 0
