"""vive_tracker_cali.py
ViveTracker 定位标定面板组件

功能：
- 提供 VR 追踪器的定位标定功能
- 支持位置和旋转校准
"""

from calibration_widget import CalibrationWidget


class ViveTrackerCaliWidget(CalibrationWidget):
    """定位标定面板组件（CalibrationWidget 的包装）。
    
    此类是 CalibrationWidget 的直接包装，保持所有原有功能。
    """
    
    def __init__(self, vive_tracker_widget=None, parent=None):
        """初始化定位标定面板。
        
        Args:
            vive_tracker_widget: ViveTrackerWidget 实例，用于访问追踪数据
            parent: 父窗口
        """
        super().__init__(vive_tracker_widget=vive_tracker_widget, parent=parent)
