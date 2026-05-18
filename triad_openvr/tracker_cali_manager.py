"""tracker_cali_manager.py
Vive Tracker 全局标定偏移管理器。

管理对所有 Vive Tracker 共同生效的四元数偏移：
- 位置偏移四元数 quat_location_bias
- 附加旋转四元数 quat_additional
"""

from dataclasses import dataclass
from threading import RLock
from typing import Optional


@dataclass
class TrackerCaliState:
    """全局 Tracker 标定偏移状态。"""

    pos_bias_x_m: float = 0.0  # 共享位置偏差 X 分量（米，应用于所有 Tracker）
    pos_bias_y_m: float = 0.0  # 共享位置偏差 Y 分量（米，应用于所有 Tracker）
    pos_bias_z_m: float = 0.0  # 共享位置偏差 Z 分量（米，应用于所有 Tracker）
    quat_location_bias_w: float = 0.382683  # 位置偏移四元数 W 分量（用于旋转最终位置）
    quat_location_bias_x: float = 0.0  # 位置偏移四元数 X 分量
    quat_location_bias_y: float = -0.923880  # 位置偏移四元数 Y 分量
    quat_location_bias_z: float = 0.0  # 位置偏移四元数 Z 分量
    quat_additional_w: float = 0.7071  # 附加旋转四元数 W 分量（额外的旋转修正）
    quat_additional_x: float = 0.7071  # 附加旋转四元数 X 分量
    quat_additional_y: float = 0.0  # 附加旋转四元数 Y 分量
    quat_additional_z: float = 0.0  # 附加旋转四元数 Z 分量


class TrackerCaliManager:
    """管理对所有 Vive Tracker 共享的标定偏移四元数。"""

    def __init__(self) -> None:
        self._lock = RLock()
        self._state = TrackerCaliState()

    def get_location_bias_quaternion_wxyz(self) -> tuple[float, float, float, float]:
        """返回位置偏移四元数 (w, x, y, z)。"""
        with self._lock:
            return (
                self._state.quat_location_bias_w,
                self._state.quat_location_bias_x,
                self._state.quat_location_bias_y,
                self._state.quat_location_bias_z,
            )

    def set_location_bias_quaternion_wxyz(
        self,
        quat_wxyz: tuple[float, float, float, float],
    ) -> None:
        """设置位置偏移四元数 (w, x, y, z)。"""
        with self._lock:
            self._state.quat_location_bias_w = quat_wxyz[0]
            self._state.quat_location_bias_x = quat_wxyz[1]
            self._state.quat_location_bias_y = quat_wxyz[2]
            self._state.quat_location_bias_z = quat_wxyz[3]

    def get_position_bias_xyz(self) -> tuple[float, float, float]:
        """返回共享位置偏差 (x, y, z)。"""
        with self._lock:
            return (
                self._state.pos_bias_x_m,
                self._state.pos_bias_y_m,
                self._state.pos_bias_z_m,
            )

    def set_position_bias_xyz(self, bias_xyz: tuple[float, float, float]) -> None:
        """设置共享位置偏差 (x, y, z)。"""
        with self._lock:
            self._state.pos_bias_x_m = bias_xyz[0]
            self._state.pos_bias_y_m = bias_xyz[1]
            self._state.pos_bias_z_m = bias_xyz[2]

    def get_additional_quaternion_wxyz(self) -> tuple[float, float, float, float]:
        """返回附加旋转四元数 (w, x, y, z)。"""
        with self._lock:
            return (
                self._state.quat_additional_w,
                self._state.quat_additional_x,
                self._state.quat_additional_y,
                self._state.quat_additional_z,
            )

    def set_additional_quaternion_wxyz(
        self,
        quat_wxyz: tuple[float, float, float, float],
    ) -> None:
        """设置附加旋转四元数 (w, x, y, z)。"""
        with self._lock:
            self._state.quat_additional_w = quat_wxyz[0]
            self._state.quat_additional_x = quat_wxyz[1]
            self._state.quat_additional_y = quat_wxyz[2]
            self._state.quat_additional_z = quat_wxyz[3]

    def get_state_snapshot(self) -> TrackerCaliState:
        """返回当前全局标定偏移快照。"""
        with self._lock:
            return TrackerCaliState(
                pos_bias_x_m=self._state.pos_bias_x_m,
                pos_bias_y_m=self._state.pos_bias_y_m,
                pos_bias_z_m=self._state.pos_bias_z_m,
                quat_location_bias_w=self._state.quat_location_bias_w,
                quat_location_bias_x=self._state.quat_location_bias_x,
                quat_location_bias_y=self._state.quat_location_bias_y,
                quat_location_bias_z=self._state.quat_location_bias_z,
                quat_additional_w=self._state.quat_additional_w,
                quat_additional_x=self._state.quat_additional_x,
                quat_additional_y=self._state.quat_additional_y,
                quat_additional_z=self._state.quat_additional_z,
            )


_global_tracker_cali_manager: Optional[TrackerCaliManager] = None


def get_global_tracker_cali_manager() -> TrackerCaliManager:
    """返回全局 TrackerCaliManager 实例。"""
    global _global_tracker_cali_manager
    if _global_tracker_cali_manager is None:
        _global_tracker_cali_manager = TrackerCaliManager()
    return _global_tracker_cali_manager


def reset_global_tracker_cali_manager() -> None:
    """重置全局 TrackerCaliManager 实例。"""
    global _global_tracker_cali_manager
    _global_tracker_cali_manager = None
