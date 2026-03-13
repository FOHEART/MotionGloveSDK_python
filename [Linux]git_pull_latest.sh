#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "[fetch_latest] Fetching latest from origin..."

git fetch origin || { echo "[ERROR] git fetch failed."; exit 1; }

git pull origin main || { echo "[ERROR] git pull failed."; exit 1; }

echo ""
echo "[fetch_latest] Done. Current status:"
git log --oneline -5
