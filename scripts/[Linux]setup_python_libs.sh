#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "[1/2] 安装运行时依赖到 libs/ ..."
# 以下版本针对 Python 3.10 适配（部分包的更高版本需要 Python 3.11+）
# Pin NumPy to 1.26.x to avoid ABI incompatibilities with prebuilt
# extensions that were compiled against NumPy 1.x (see CI logs).
pip3 install vtk==9.6.0 numpy==1.26.4 matplotlib==3.10.8 Pillow==12.1.1 \
    pyparsing==3.3.2 python-dateutil==2.9.0.post0 packaging==26.0 \
    fonttools==4.62.0 contourpy==1.3.2 cycler==0.12.1 kiwisolver==1.4.9 six==1.17.0 \
    pyside6==6.5.3 \
    --target "$ROOT_DIR/libs"

echo
echo "[2/2] 安装开发工具到系统 Python（pyinstaller、pybind11）..."
pip3 install pyinstaller==6.19.0 pybind11==2.13.6

echo
echo "Done."
