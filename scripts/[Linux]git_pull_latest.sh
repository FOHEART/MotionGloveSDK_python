#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "[fetch_latest] Fetching latest from origin..."

git fetch origin || { echo "[ERROR] git fetch failed."; exit 1; }

git pull origin main || { echo "[ERROR] git pull failed."; exit 1; }

echo "[fetch_latest] Syncing submodules (third_party/MotionGloveSDK_cpp)..."
git submodule update --init --recursive || { echo "[ERROR] git submodule update failed."; exit 1; }

echo "[fetch_latest] Rebuilding native library..."
bash "$ROOT_DIR/scripts/[Linux]build_mgsdk_cpp.sh" || { echo "[ERROR] native library build failed."; exit 1; }

echo ""
echo "[fetch_latest] Done. Current status:"
git log --oneline -5
