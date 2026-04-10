"""draw_config_io.py
绘图配置的数据结构定义及 JSON 序列化/反序列化。

公开接口
--------
DrawConfig          — dataclass，持有所有绘制属性
save_config(config, path)   — 写出 JSON 文件
load_config(path)           — 读取 JSON 文件，缺字段时用默认值填充
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class DrawConfig:
    """VTK 绘制属性配置。颜色为 (r, g, b) float 元组，范围 0.0–1.0。"""

    joint_radius: float = 0.005
    joint_color: tuple[float, float, float] = field(default_factory=lambda: (1.0, 1.0, 1.0))
    link_width: float = 2.0
    link_color: tuple[float, float, float] = field(default_factory=lambda: (0.7, 0.7, 0.7))
    axis_length: float = 0.010

    @classmethod
    def default(cls) -> DrawConfig:
        """返回出厂默认配置。"""
        return cls()


def save_config(config: DrawConfig, path: str) -> None:
    """将 DrawConfig 序列化为 JSON 文件。

    参数：
        config  — 要保存的配置
        path    — 目标文件路径（不存在则创建，已存在则覆盖）

    异常：
        OSError — 路径无效或权限不足时抛出
    """
    data = {
        "joint_radius": config.joint_radius,
        "joint_color": list(config.joint_color),
        "link_width": config.link_width,
        "link_color": list(config.link_color),
        "axis_length": config.axis_length,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_config(path: str) -> DrawConfig:
    """从 JSON 文件加载 DrawConfig。

    参数：
        path — 源文件路径

    返回：
        DrawConfig — 缺失字段用默认值填充

    异常：
        FileNotFoundError — 文件不存在时抛出
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    defaults = DrawConfig.default()

    def _get(key, default_val):
        return data.get(key, default_val)

    def _get_color(key, default_val):
        v = data.get(key)
        if v is not None and len(v) == 3:
            return tuple(float(c) for c in v)
        return default_val

    return DrawConfig(
        joint_radius=float(_get("joint_radius", defaults.joint_radius)),
        joint_color=_get_color("joint_color", defaults.joint_color),
        link_width=float(_get("link_width", defaults.link_width)),
        link_color=_get_color("link_color", defaults.link_color),
        axis_length=float(_get("axis_length", defaults.axis_length)),
    )
