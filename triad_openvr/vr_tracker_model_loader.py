"""VR Tracker OBJ 模型加载器 - 负责在 VTK 场景中加载和管理追踪器模型。

功能：
- 从 OBJ 文件加载 VR 追踪器 3D 模型
- 根据四元数和位置更新模型的位置和旋转
- 支持添加/删除模型到/从 VTK 渲染器
"""

import sys
from pathlib import Path
from typing import Optional, Tuple

# 导入 VTK
try:
    import vtk
except ImportError:
    vtk = None


class VRTrackerModelActor:
    """VR Tracker 3D 模型 Actor 包装类。
    
    负责加载、变换和管理 OBJ 模型在 VTK 中的显示。
    """
    
    def __init__(self, model_path: str = None):
        """初始化模型 Actor。
        
        Args:
            model_path: OBJ 模型文件路径。如果为 None，会自动查找默认路径。
        """
        if vtk is None:
            raise RuntimeError("VTK 未安装，无法加载 3D 模型")
        
        self._actor = None
        self._mapper = None
        self._transform = None
        self._model_path = model_path or self._find_default_model_path()
        
        if self._model_path is None or not Path(self._model_path).exists():
            raise FileNotFoundError(f"无法找到 VR Tracker OBJ 模型：{model_path}")
        
        self._load_model()
    
    @staticmethod
    def _find_default_model_path() -> Optional[str]:
        """查找默认的 OBJ 模型路径。"""
        candidates = [
            Path(__file__).parent / "vr_tracker_vive_3_0" / "vr_tracker_vive_3_0.obj",
            Path(__file__).parent.parent / "triad_openvr" / "vr_tracker_vive_3_0" / "vr_tracker_vive_3_0.obj",
            Path.cwd() / "triad_openvr" / "vr_tracker_vive_3_0" / "vr_tracker_vive_3_0.obj",
        ]
        
        for candidate in candidates:
            try:
                if candidate.exists():
                    return str(candidate)
            except Exception:
                continue
        
        return None
    
    def _load_model(self):
        """从 OBJ 文件加载模型。"""
        try:
            # 读取 OBJ 文件
            reader = vtk.vtkOBJReader()
            reader.SetFileName(self._model_path)
            reader.Update()
            
            # 创建 mapper
            self._mapper = vtk.vtkPolyDataMapper()
            self._mapper.SetInputConnection(reader.GetOutputPort())
            
            # 创建 actor
            self._actor = vtk.vtkActor()
            self._actor.SetMapper(self._mapper)
            
            # 初始化变换矩阵
            self._transform = vtk.vtkTransform()
            self._actor.SetUserTransform(self._transform)
            
            # 设置颜色（可选：浅蓝色）
            self._actor.GetProperty().SetColor(0.5, 0.7, 1.0)
            self._actor.GetProperty().EdgeVisibilityOff()
            
            print(f"[ModelLoader] ✓ 模型已加载：{self._model_path}")
        except Exception as e:
            print(f"[ModelLoader] ✗ 加载模型失败：{e}")
            raise
    
    def get_actor(self) -> vtk.vtkActor:
        """获取 VTK Actor 对象。"""
        return self._actor
    
    def set_position_and_rotation(self, position: Tuple[float, float, float], 
                                   quat: Tuple[float, float, float, float]):
        """设置模型的位置和旋转。
        
        Args:
            position: 位置 (x, y, z)，单位：米
            quat: 四元数 (qx, qy, qz, qw)
        """
        if self._transform is None:
            return
        
        try:
            qx, qy, qz, qw = quat
            
            # 标准化四元数
            quat_norm = (qx*qx + qy*qy + qz*qz + qw*qw) ** 0.5
            if quat_norm > 1e-6:
                qx /= quat_norm
                qy /= quat_norm
                qz /= quat_norm
                qw /= quat_norm
            
            # 手动将四元数转换为 3x3 旋转矩阵
            # 根据公式：
            # https://en.wikipedia.org/wiki/Quaternions_and_spatial_rotation#Quaternion-derived_rotation_matrix
            r11 = 1 - 2*(qy*qy + qz*qz)
            r12 = 2*(qx*qy - qz*qw)
            r13 = 2*(qx*qz + qy*qw)
            
            r21 = 2*(qx*qy + qz*qw)
            r22 = 1 - 2*(qx*qx + qz*qz)
            r23 = 2*(qy*qz - qx*qw)
            
            r31 = 2*(qx*qz - qy*qw)
            r32 = 2*(qy*qz + qx*qw)
            r33 = 1 - 2*(qx*qx + qy*qy)
            
            # 创建 4x4 矩阵：旋转部分（3x3）+ 位置部分
            matrix = vtk.vtkMatrix4x4()
            
            # 设置旋转部分 (3x3)
            matrix.SetElement(0, 0, r11)
            matrix.SetElement(0, 1, r12)
            matrix.SetElement(0, 2, r13)
            
            matrix.SetElement(1, 0, r21)
            matrix.SetElement(1, 1, r22)
            matrix.SetElement(1, 2, r23)
            
            matrix.SetElement(2, 0, r31)
            matrix.SetElement(2, 1, r32)
            matrix.SetElement(2, 2, r33)
            
            # 设置位置部分 (第 4 列)
            matrix.SetElement(0, 3, position[0])
            matrix.SetElement(1, 3, position[1])
            matrix.SetElement(2, 3, position[2])
            
            # 设置齐次坐标
            matrix.SetElement(3, 0, 0.0)
            matrix.SetElement(3, 1, 0.0)
            matrix.SetElement(3, 2, 0.0)
            matrix.SetElement(3, 3, 1.0)
            
            # 应用矩阵到变换
            self._transform.SetMatrix(matrix)
            
        except Exception as e:
            print(f"[ModelLoader] ✗ 更新位置/旋转失败：{e}")
            import traceback
            traceback.print_exc()


def create_tracker_actor(tracker_name: str, model_path: str = None) -> Optional[VRTrackerModelActor]:
    """创建 VR Tracker 模型 Actor。
    
    Args:
        tracker_name: 追踪器名称（用于日志）
        model_path: OBJ 模型文件路径
        
    Returns:
        VRTrackerModelActor 实例，或创建失败时返回 None
    """
    try:
        actor = VRTrackerModelActor(model_path)
        print(f"[ModelLoader] ✓ 为 '{tracker_name}' 创建了模型 Actor")
        return actor
    except Exception as e:
        print(f"[ModelLoader] ✗ 无法为 '{tracker_name}' 创建模型 Actor：{e}")
        return None
