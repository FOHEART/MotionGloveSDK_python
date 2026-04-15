#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Control console window visibility via argument.
# Usage: build_dist.sh [--console]
# Default: no console window (--noconsole)
CONSOLE_FLAG="--noconsole"
if [ "${1:-}" = "--console" ]; then
    CONSOLE_FLAG="--console"
fi

echo "[build] Packaging motionGloveSDK_example3_3dView with PyInstaller..."
echo "[build] ROOT_DIR = $ROOT_DIR"
echo "[build] Console window: $CONSOLE_FLAG"

pyinstaller \
    --noconfirm \
    --clean \
    --onedir \
    $CONSOLE_FLAG \
    --name "MotionGlove3DViewer" \
    --distpath "$ROOT_DIR/dist" \
    --workpath "$ROOT_DIR/build" \
    --specpath "$ROOT_DIR/build" \
    --paths "$ROOT_DIR/libs" \
    --paths "$ROOT_DIR/src" \
    --paths "$ROOT_DIR/python_draw3d" \
    --paths "$ROOT_DIR/ui" \
    --add-data "$ROOT_DIR/fonts:fonts" \
    --add-data "$ROOT_DIR/ui/left_panel.ui:ui" \
    --hidden-import vtkmodules.all \
    --hidden-import vtkmodules.qt.QVTKRenderWindowInteractor \
    --hidden-import PySide6.QtWidgets \
    --hidden-import PySide6.QtCore \
    --hidden-import PySide6.QtGui \
    --collect-all vtk \
    --collect-all vtkmodules \
    --collect-all PySide6 \
    "$ROOT_DIR/motionGloveSDK_example3_3dView.py"

echo
echo "[build] Done. Output: $ROOT_DIR/dist/MotionGlove3DViewer/"
