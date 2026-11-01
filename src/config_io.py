"""@file  config_io.py
@brief  项目根目录 config.json 的原子读写。
@details
提供 read_config() / write_config()。写入采用「临时文件 + os.replace
原子替换」，避免读到写了一半的配置。读取容错：文件不存在、JSON 损坏、
JSON 为 null 时一律返回空字典，绝不抛异常——上层不应因配置问题崩溃。

测试：tests/unit/test_config_io.py。
"""
import os
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_PATH = os.path.join(ROOT, "config.json")


def read_config():
    """@brief 读取 config.json，异常时回退空配置。

    @return dict：配置内容；文件不存在 / JSON 非法 / 内容为 null 时返回 {}。
    """
    try:
        if not os.path.exists(CONFIG_PATH):
            return {}
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        # Corrupt or unreadable config -> return empty dict
        return {}


def write_config(cfg: dict):
    """@brief 原子写入 config.json（先写 .tmp 再 os.replace）。

    @param cfg 待写入的配置字典（会被 json 序列化，非 ASCII 原样保存）。
    @return    无（None）。
    """
    tmp = CONFIG_PATH + ".tmp"
    # Ensure parent dir exists (should be project root)
    d = os.path.dirname(CONFIG_PATH)
    os.makedirs(d, exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, CONFIG_PATH)
