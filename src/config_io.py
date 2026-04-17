"""Simple config IO for project root `config.json`.

Provides `read_config()` and `write_config()` with atomic writes.
"""
import os
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_PATH = os.path.join(ROOT, "config.json")


def read_config():
    try:
        if not os.path.exists(CONFIG_PATH):
            return {}
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        # Corrupt or unreadable config -> return empty dict
        return {}


def write_config(cfg: dict):
    tmp = CONFIG_PATH + ".tmp"
    # Ensure parent dir exists (should be project root)
    d = os.path.dirname(CONFIG_PATH)
    os.makedirs(d, exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, CONFIG_PATH)
