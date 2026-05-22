#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="$ROOT_DIR/libs:$ROOT_DIR/src:$PYTHONPATH"

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
    --distpath "$ROOT_DIR/dist" \
    --workpath "$ROOT_DIR/build" \
    "$ROOT_DIR/MotionGlove3DViewer.spec"

cp "$ROOT_DIR/config.json" "$ROOT_DIR/dist/MotionGlove3DViewer/config.json"
mkdir -p "$ROOT_DIR/dist/MotionGlove3DViewer/_internal/triad_openvr"
cp -r "$ROOT_DIR/triad_openvr/lh_basestation_vive" "$ROOT_DIR/dist/MotionGlove3DViewer/_internal/triad_openvr/"
cp -r "$ROOT_DIR/triad_openvr/vr_tracker_vive_3_0" "$ROOT_DIR/dist/MotionGlove3DViewer/_internal/triad_openvr/"

echo
echo "[build] Done. Output: $ROOT_DIR/dist/MotionGlove3DViewer/"
