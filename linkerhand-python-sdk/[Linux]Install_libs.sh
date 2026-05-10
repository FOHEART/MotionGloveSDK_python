#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
REQ_FILE="$ROOT_DIR/requirements.txt"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 未安装，请先安装 Python 3.10+。" >&2
    exit 1
fi

if ! command -v pip3 >/dev/null 2>&1; then
    echo "pip3 未安装，请先安装 python3-pip。" >&2
    exit 1
fi

if [ ! -f "$REQ_FILE" ]; then
    echo "未找到 requirements.txt: $REQ_FILE" >&2
    exit 1
fi

if command -v apt-get >/dev/null 2>&1; then
    echo "[1/3] 安装系统依赖 python3-pip 和 python-is-python3 ..."
    if [ "$(id -u)" -eq 0 ]; then
        apt-get update
        apt-get install -y python3-pip python-is-python3
    elif command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; then
        sudo -n apt-get update
        sudo -n apt-get install -y python3-pip python-is-python3
    elif [ -t 0 ]; then
        sudo apt-get update
        sudo apt-get install -y python3-pip python-is-python3
    else
        echo "跳过系统依赖安装：当前环境无法交互输入 sudo 密码。" >&2
        echo "如需安装，请手动执行：sudo apt-get update && sudo apt-get install -y python3-pip python-is-python3" >&2
    fi
    echo
fi

echo "[2/3] 升级 pip/setuptools/wheel ..."
python3 -m pip install --upgrade pip setuptools wheel

echo
echo "[3/3] 根据 requirements.txt 安装依赖 ..."
python3 -m pip install -r "$REQ_FILE"

echo
echo "Done."