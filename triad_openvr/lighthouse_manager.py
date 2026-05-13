"""lighthouse_manager.py
LightHouse 基站统一管理结构体和管理器

此模块定义了 LighthouseData 结构体，用于统一管理 LightHouse 基站的各项信息：
- 基站名称（Tracking Reference 名称）
- 序列号
- 实时位置（x, y, z）
- 旋转欧拉角（yaw, pitch, roll）
- 旋转四元数（w, x, y, z）
- 在线状态

同时提供 LighthouseManager 类用于集中管理多个基站。
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import numpy as np


@dataclass
class LighthouseData:
    """LightHouse 基站数据结构。
    
    包含基站的所有关键信息，支持实时更新和查询。
    """
    
    # 基本信息
    name: str = ""              # 基站名称（如："Tracking Reference 1"）
    serial: str = ""            # 序列号
    
    # 位置信息（单位：米）
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    
    # 位置偏差信息（单位：米）
    position_bias_x_m: float = 0.0
    position_bias_y_m: float = 0.0
    position_bias_z_m: float = 0.0
    
    # 最终位置（原始位置 + 偏差）（单位：米）
    position_final_x_m: float = 0.0
    position_final_y_m: float = 0.0
    position_final_z_m: float = 0.0
    
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
    is_online: bool = False      # 是否在线
    valid: bool = False          # 数据是否有效
    
    # 时间戳
    timestamp: float = 0.0       # 最后更新时间
    
    # 备注信息
    remarks: str = ""            # 备注
    
    def __post_init__(self):
        """初始化旋转矩阵为单位矩阵。"""
        if self.rotation_matrix is None:
            self.rotation_matrix = np.eye(3, dtype=np.float32)
        # 初始化最终位置
        self._update_final_position()
    
    def _update_final_position(self):
        """内部方法：计算最终位置（原始位置 + 偏差）。"""
        self.position_final_x_m = self.position_x + self.position_bias_x_m
        self.position_final_y_m = self.position_y + self.position_bias_y_m
        self.position_final_z_m = self.position_z + self.position_bias_z_m
    
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
        # 更新最终位置
        self._update_final_position()
    
    def update_position_bias(self, x_bias: float, y_bias: float, z_bias: float):
        """更新位置偏差信息。
        
        Args:
            x_bias: X 轴偏差（米）
            y_bias: Y 轴偏差（米）
            z_bias: Z 轴偏差（米）
        """
        self.position_bias_x_m = x_bias
        self.position_bias_y_m = y_bias
        self.position_bias_z_m = z_bias
        # 更新最终位置
        self._update_final_position()
    
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
        """获取原始位置信息。
        
        Returns:
            (x, y, z) 元组
        """
        return (self.position_x, self.position_y, self.position_z)
    
    def get_position_bias(self) -> Tuple[float, float, float]:
        """获取位置偏差信息。
        
        Returns:
            (x_bias, y_bias, z_bias) 元组
        """
        return (self.position_bias_x_m, self.position_bias_y_m, self.position_bias_z_m)
    
    def get_position_final(self) -> Tuple[float, float, float]:
        """获取最终位置信息（用于 VTK 显示）。
        
        Returns:
            (x_final, y_final, z_final) 元组
        """
        return (self.position_final_x_m, self.position_final_y_m, self.position_final_z_m)
    
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
            f"LighthouseData: {self.name}",
            f"  序列号: {self.serial}",
            f"  原始位置: ({self.position_x:.4f}, {self.position_y:.4f}, {self.position_z:.4f}) m",
            f"  位置偏差: ({self.position_bias_x_m:.4f}, {self.position_bias_y_m:.4f}, {self.position_bias_z_m:.4f}) m",
            f"  最终位置: ({self.position_final_x_m:.4f}, {self.position_final_y_m:.4f}, {self.position_final_z_m:.4f}) m",
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
        return (f"LighthouseData(name='{self.name}', serial='{self.serial}', "
                f"pos=({self.position_x:.2f}, {self.position_y:.2f}, {self.position_z:.2f}), "
                f"final=({self.position_final_x_m:.2f}, {self.position_final_y_m:.2f}, {self.position_final_z_m:.2f}), "
                f"quat=({self.quat_w:.2f}, {self.quat_x:.2f}, {self.quat_y:.2f}, {self.quat_z:.2f}), "
                f"online={self.is_online})")


class LighthouseManager:
    """LightHouse 基站管理器。
    
    集中管理多个基站，使用基站名称作为 key，LighthouseData 实例作为 value。
    """
    
    def __init__(self):
        """初始化管理器。"""
        self._lighthouses: Dict[str, LighthouseData] = {}
        self._last_content: str = ""  # 缓存的基站信息内容
    
    def register_lighthouse(self, name: str, serial: str = "") -> LighthouseData:
        """注册一个新的基站。
        
        Args:
            name: 基站名称（如："Tracking Reference 1"）
            serial: 序列号
        
        Returns:
            LighthouseData 实例
        """
        if name not in self._lighthouses:
            lighthouse = LighthouseData(name=name, serial=serial)
            self._lighthouses[name] = lighthouse
            print(f"[LighthouseManager] 已注册基站：{name}")
        return self._lighthouses[name]
    
    def get_lighthouse(self, name: str) -> Optional[LighthouseData]:
        """获取指定名称的基站。
        
        Args:
            name: 基站名称
        
        Returns:
            LighthouseData 实例或 None
        """
        return self._lighthouses.get(name)
    
    def remove_lighthouse(self, name: str) -> bool:
        """移除指定名称的基站。
        
        Args:
            name: 基站名称
        
        Returns:
            是否成功移除
        """
        if name in self._lighthouses:
            del self._lighthouses[name]
            print(f"[LighthouseManager] 已移除基站：{name}")
            return True
        return False
    
    def get_all_lighthouses(self) -> Dict[str, LighthouseData]:
        """获取所有基站。
        
        Returns:
            {name: LighthouseData} 字典
        """
        return self._lighthouses.copy()
    
    def get_online_lighthouses(self) -> Dict[str, LighthouseData]:
        """获取所有在线的基站。
        
        Returns:
            {name: LighthouseData} 字典，仅包含在线的基站
        """
        return {name: lighthouse for name, lighthouse in self._lighthouses.items() if lighthouse.is_online}
    
    def update_from_dict_list(self, lighthouse_dicts: list) -> bool:
        """从字典列表更新基站信息。
        
        Args:
            lighthouse_dicts: 列表，每个元素为字典，包含：
                {
                    "id": str,                  # 基站 ID（通常是序列号）
                    "name": str,                # 基站名称
                    "serial": str,              # 序列号
                    "position": (x, y, z),     # 位置
                    "quat_wxyz": (w, x, y, z)  # 四元数
                }
        
        Returns:
            是否有更新
        """
        has_update = False
        
        # 先清空或标记所有基站为离线
        current_names = set()
        for lighthouse_dict in lighthouse_dicts:
            name = lighthouse_dict.get("name", "")
            if name:
                current_names.add(name)
        
        # 更新接收到的基站
        for lighthouse_dict in lighthouse_dicts:
            name = lighthouse_dict.get("name", "")
            if not name:
                continue
            
            serial = lighthouse_dict.get("serial", "")
            position = lighthouse_dict.get("position", (0, 0, 0))
            quat_wxyz = lighthouse_dict.get("quat_wxyz", (1, 0, 0, 0))
            
            # 注册或获取基站
            if name not in self._lighthouses:
                self.register_lighthouse(name, serial)
                has_update = True
            
            lighthouse = self._lighthouses[name]
            
            # 更新数据
            old_online = lighthouse.is_online
            lighthouse.is_online = True
            lighthouse.valid = True
            lighthouse.update_position(position[0], position[1], position[2])
            lighthouse.update_quat(quat_wxyz[0], quat_wxyz[1], quat_wxyz[2], quat_wxyz[3])
            lighthouse.timestamp = __import__('time').time()
            
            if not old_online:
                has_update = True
        
        # 标记不在列表中的基站为离线
        for name, lighthouse in self._lighthouses.items():
            if name not in current_names and lighthouse.is_online:
                lighthouse.is_online = False
                has_update = True
        
        return has_update
    
    def set_last_content(self, content: str):
        """设置缓存的基站信息内容。
        
        Args:
            content: 基站信息内容字符串
        """
        self._last_content = content
    
    def get_last_content(self) -> str:
        """获取缓存的基站信息内容。
        
        Returns:
            基站信息内容字符串
        """
        return self._last_content
    
    def clear(self):
        """清空所有基站。"""
        self._lighthouses.clear()
        self._last_content = ""
        print("[LighthouseManager] 已清空所有基站")
    
    def print_summary(self):
        """打印所有基站的摘要信息。"""
        print("\n" + "=" * 60)
        print("LightHouse 管理器摘要")
        print("=" * 60)
        
        if not self._lighthouses:
            print("无基站")
        else:
            for name, lighthouse in self._lighthouses.items():
                print(f"\n{lighthouse}")
        
        print("=" * 60 + "\n")


# 全局管理器实例
_global_lighthouse_manager: Optional[LighthouseManager] = None


def get_global_lighthouse_manager() -> LighthouseManager:
    """获取全局 LighthouseManager 实例（单例）。
    
    Returns:
        LighthouseManager 实例
    """
    global _global_lighthouse_manager
    if _global_lighthouse_manager is None:
        _global_lighthouse_manager = LighthouseManager()
        print("[LighthouseManager] 全局实例已初始化")
    return _global_lighthouse_manager
