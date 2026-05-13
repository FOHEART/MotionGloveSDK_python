"""tracker_manager.py
VR Tracker 统一管理结构体和管理器

此模块定义了 ViveTrackerMgr 结构体，用于统一管理 Vive Tracker 的各项信息：
- 追踪器名称
- 实时位置（x, y, z）
- 旋转欧拉角（yaw, pitch, roll）
- 旋转矩阵（3x3 numpy 数组或 VTK 矩阵）
- 四元数（w, x, y, z）
- 在线状态

同时提供 TrackerManager 类用于集中管理多个追踪器。
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import numpy as np


@dataclass
class TrackerData:
    """追踪器数据结构（用于实时追踪线程）。"""
    pos_origin_x_m: float = 0.0
    pos_origin_y_m: float = 0.0
    pos_origin_z_m: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    quat_origin_w: float = 0.0
    quat_origin_x: float = 0.0
    quat_origin_y: float = 0.0
    quat_origin_z: float = 0.0
    pos_bias_x_m: float = 0.0  # 位置偏差 X 坐标（米）
    pos_bias_y_m: float = 0.0  # 位置偏差 Y 坐标（米）
    pos_bias_z_m: float = 0.0  # 位置偏差 Z 坐标（米）
    valid: bool = False


@dataclass
class ViveTrackerMgr:
    """Vive Tracker 统一管理结构体。
    
    包含追踪器的所有关键信息，支持实时更新和查询。
    """
    
    # 基本信息
    name: str = ""  # 追踪器名称（如："left", "right"）
    
    # 位置信息（单位：米）
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    
    # 旋转信息 - 欧拉角（单位：度）
    euler_yaw: float = 0.0      # 偏航角
    euler_pitch: float = 0.0    # 俯仰角
    euler_roll: float = 0.0     # 翻滚角
    
    # 旋转信息 - 四元数（标准格式 w, x, y, z）
    quat_w: float = 1.0
    quat_x: float = 0.0
    quat_y: float = 0.0
    quat_z: float = 0.0
    
    # 旋转信息 - 旋转矩阵（3x3，使用 numpy 数组）
    rotation_matrix: Optional[np.ndarray] = None
    
    # 状态信息
    is_online: bool = False  # 是否在线
    valid: bool = False      # 数据是否有效
    
    # 时间戳
    timestamp: float = 0.0   # 最后更新时间
    
    # 备注信息
    remarks: str = ""        # 备注
    
    def __post_init__(self):
        """初始化旋转矩阵为单位矩阵。"""
        if self.rotation_matrix is None:
            self.rotation_matrix = np.eye(3, dtype=np.float32)
    
    def update_position(self, x: float, y: float, z: float):
        """更新位置信息。
        
        Args:
            x: X 坐标（米）
            y: Y 坐标（米）
            z: Z 坐标（米）
        """
        self.position_x = x
        self.position_y = y
        self.position_z = z
    
    def update_euler(self, yaw: float, pitch: float, roll: float):
        """更新欧拉角信息。
        
        Args:
            yaw: 偏航角（度）
            pitch: 俯仰角（度）
            roll: 翻滚角（度）
        """
        self.euler_yaw = yaw
        self.euler_pitch = pitch
        self.euler_roll = roll
    
    def update_quat(self, w: float, x: float, y: float, z: float):
        """更新四元数信息。
        
        Args:
            w: W 分量
            x: X 分量
            y: Y 分量
            z: Z 分量
        """
        self.quat_w = w
        self.quat_x = x
        self.quat_y = y
        self.quat_z = z
    
    def update_rotation_matrix(self, matrix: np.ndarray):
        """更新旋转矩阵信息。
        
        Args:
            matrix: 3x3 旋转矩阵（numpy 数组）
        """
        if matrix.shape == (3, 3):
            self.rotation_matrix = matrix.copy()
        else:
            raise ValueError(f"期望 3x3 矩阵，得到 {matrix.shape}")
    
    def get_position(self) -> Tuple[float, float, float]:
        """获取位置信息。
        
        Returns:
            (x, y, z) 元组
        """
        return (self.position_x, self.position_y, self.position_z)
    
    def get_euler(self) -> Tuple[float, float, float]:
        """获取欧拉角信息。
        
        Returns:
            (yaw, pitch, roll) 元组（度）
        """
        return (self.euler_yaw, self.euler_pitch, self.euler_roll)
    
    def get_quat(self) -> Tuple[float, float, float, float]:
        """获取四元数信息。
        
        Returns:
            (w, x, y, z) 元组
        """
        return (self.quat_w, self.quat_x, self.quat_y, self.quat_z)
    
    def get_rotation_matrix(self) -> np.ndarray:
        """获取旋转矩阵信息。
        
        Returns:
            3x3 旋转矩阵（numpy 数组）
        """
        return self.rotation_matrix.copy() if self.rotation_matrix is not None else np.eye(3)
    
    def __str__(self) -> str:
        """格式化为字符串表示。"""
        lines = [
            f"ViveTrackerMgr: {self.name}",
            f"  位置: ({self.position_x:.4f}, {self.position_y:.4f}, {self.position_z:.4f}) m",
            f"  欧拉角: Yaw={self.euler_yaw:.2f}° Pitch={self.euler_pitch:.2f}° Roll={self.euler_roll:.2f}°",
            f"  四元数: w={self.quat_w:.4f} x={self.quat_x:.4f} y={self.quat_y:.4f} z={self.quat_z:.4f}",
            f"  在线状态: {'在线' if self.is_online else '离线'}",
            f"  数据有效: {'是' if self.valid else '否'}",
        ]
        if self.remarks:
            lines.append(f"  备注: {self.remarks}")
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        """调试表示。"""
        return (f"ViveTrackerMgr(name='{self.name}', pos=({self.position_x:.2f}, {self.position_y:.2f}, "
                f"{self.position_z:.2f}), quat=({self.quat_w:.2f}, {self.quat_x:.2f}, {self.quat_y:.2f}, "
                f"{self.quat_z:.2f}), online={self.is_online})")


class TrackerManager:
    """Vive Tracker 管理器。
    
    集中管理多个 Tracker，使用 tracker 名称作为 key，ViveTrackerMgr 实例作为 value。
    """
    
    def __init__(self):
        """初始化管理器。"""
        self._trackers: Dict[str, ViveTrackerMgr] = {}
    
    def register_tracker(self, name: str) -> ViveTrackerMgr:
        """注册一个新的追踪器。
        
        Args:
            name: 追踪器名称（如："left", "right", "waist"）
        
        Returns:
            ViveTrackerMgr 实例
        """
        if name not in self._trackers:
            tracker = ViveTrackerMgr(name=name)
            self._trackers[name] = tracker
            print(f"[TrackerManager] 已注册追踪器：{name}")
        return self._trackers[name]
    
    def get_tracker(self, name: str) -> Optional[ViveTrackerMgr]:
        """获取指定名称的追踪器。
        
        Args:
            name: 追踪器名称
        
        Returns:
            ViveTrackerMgr 实例或 None
        """
        return self._trackers.get(name)
    
    def remove_tracker(self, name: str) -> bool:
        """移除指定名称的追踪器。
        
        Args:
            name: 追踪器名称
        
        Returns:
            是否成功移除
        """
        if name in self._trackers:
            del self._trackers[name]
            print(f"[TrackerManager] 已移除追踪器：{name}")
            return True
        return False
    
    def get_all_trackers(self) -> Dict[str, ViveTrackerMgr]:
        """获取所有追踪器。
        
        Returns:
            {name: ViveTrackerMgr} 字典
        """
        return self._trackers.copy()
    
    def get_online_trackers(self) -> Dict[str, ViveTrackerMgr]:
        """获取所有在线的追踪器。
        
        Returns:
            {name: ViveTrackerMgr} 字典，仅包含在线的追踪器
        """
        return {name: tracker for name, tracker in self._trackers.items() if tracker.is_online}
    
    def clear(self):
        """清空所有追踪器。"""
        self._trackers.clear()
        print("[TrackerManager] 已清空所有追踪器")
    
    def print_summary(self):
        """打印所有追踪器的摘要信息。"""
        print("\n" + "=" * 60)
        print("Tracker 管理器摘要")
        print("=" * 60)
        
        if not self._trackers:
            print("无追踪器")
        else:
            for name, tracker in self._trackers.items():
                print(f"\n{tracker}")
        
        print("=" * 60 + "\n")
    
    def __len__(self) -> int:
        """获取追踪器总数。"""
        return len(self._trackers)
    
    def __contains__(self, name: str) -> bool:
        """检查是否存在指定名称的追踪器。"""
        return name in self._trackers
    
    def __getitem__(self, name: str) -> ViveTrackerMgr:
        """通过 [] 操作符获取追踪器。"""
        return self._trackers[name]
    
    def __repr__(self) -> str:
        """调试表示。"""
        return f"TrackerManager(count={len(self._trackers)}, trackers={list(self._trackers.keys())})"


# 全局管理器实例（可选）
_global_tracker_manager: Optional[TrackerManager] = None


def get_global_tracker_manager() -> TrackerManager:
    """获取全局 Tracker 管理器实例。
    
    Returns:
        全局 TrackerManager 实例
    """
    global _global_tracker_manager
    if _global_tracker_manager is None:
        _global_tracker_manager = TrackerManager()
    return _global_tracker_manager


def reset_global_tracker_manager():
    """重置全局 Tracker 管理器。"""
    global _global_tracker_manager
    _global_tracker_manager = None
