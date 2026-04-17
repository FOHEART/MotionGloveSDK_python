#!/usr/bin/env bash
set -euo pipefail

# Build csv_to_bvh using PyInstaller on Linux/macOS
# Usage: scripts/[Linux]build_csv_to_bvh.sh [additional pyinstaller args]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "Building csv_to_bvh with PyInstaller..."

# Parse args and support --bundle-python to include an embeddable Python folder
FORWARDED_ARGS=()
REM Bundle Python by default; use --no-bundle-python to disable
BUNDLE_PY=1
for a in "$@"; do
  if [ "$a" = "--no-bundle-python" ]; then
    BUNDLE_PY=0
  else
    FORWARDED_ARGS+=("$a")
  fi
done

ADD_DATA_ARGS=()
if [ "$BUNDLE_PY" -eq 1 ]; then
  if [ -d "python_embed/linux" ]; then
    ADD_DATA_ARGS+=("--add-data" "python_embed/linux:python_embed/linux")
    echo "Bundling embeddable Python from python_embed/linux"
  else
    echo "Warning: --bundle-python requested but python_embed/linux not found."
  fi
fi

python3 -m PyInstaller --noconfirm --clean --onefile --console --name csv_to_bvh --paths src --hidden-import=src.csv_frame_reader --hidden-import=src.definitions --hidden-import=src.xsqeconverter "src/csv_to_bvh.py" "${ADD_DATA_ARGS[@]}" "${FORWARDED_ARGS[@]}"

# Ensure output is under dist/csv_to_bvh directory
if [ -d "dist/csv_to_bvh" ]; then
  rm -rf "dist/csv_to_bvh"
fi
mkdir -p "dist/csv_to_bvh"

if [ -f "dist/csv_to_bvh" ]; then
  mv -f "dist/csv_to_bvh" "dist/csv_to_bvh/csv_to_bvh" || true
elif [ -f "dist/csv_to_bvh/csv_to_bvh" ] || [ -f "dist/csv_to_bvh/csv_to_bvh.exe" ]; then
  # already in place
  :
else
  # PyInstaller may produce dist/csv_to_bvh (file) or dist/csv_to_bvh/csv_to_bvh
  if [ -f "dist/csv_to_bvh" ]; then
    mv -f "dist/csv_to_bvh" "dist/csv_to_bvh/csv_to_bvh" || true
  else
    echo "Warning: built executable not found in dist/"
  fi
fi

echo "Build finished. See dist/csv_to_bvh/csv_to_bvh (or csv_to_bvh.exe on Windows)."

exit 0
