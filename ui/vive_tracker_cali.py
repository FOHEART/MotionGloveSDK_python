"""vive_tracker_cali.py
ViveTracker 定位标定面板组件

功能：
- 提供 VR 追踪器的定位标定功能
- 支持位置和旋转校准
- 管理标定tab的初始化、启用和禁用
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


class CaliTabManager:
    """标定tab管理器。
    
    负责管理标定tab的创建、初始化、启用和禁用。
    """
    
    def __init__(self, vive_tracker_widget):
        """初始化标定tab管理器。
        
        Args:
            vive_tracker_widget: ViveTrackerWidget 实例
        """
        self._vive_tracker_widget = vive_tracker_widget
        self._calibration_widget = None
        self._calibration_tab_index = None
    
    def setup_calibration_tab(self, tab_widget):
        """设置标定tab。
        
        Args:
            tab_widget: QTabWidget 实例
        
        Returns:
            创建的 ViveTrackerCaliWidget 实例
        """
        # 创建标定tab
        self._calibration_widget = ViveTrackerCaliWidget(vive_tracker_widget=self._vive_tracker_widget)
        self._calibration_tab_index = tab_widget.addTab(self._calibration_widget, "定位标定")
        
        # 默认禁用定位标定 tab（只有追踪成功开启后才启用）
        tab_widget.setTabEnabled(self._calibration_tab_index, False)
        
        return self._calibration_widget
    
    def enable_calibration_tab(self, tab_widget):
        """启用标定tab（追踪成功开启）。
        
        Args:
            tab_widget: QTabWidget 实例
        """
        if self._calibration_tab_index is not None:
            tab_widget.setTabEnabled(self._calibration_tab_index, True)
    
    def disable_calibration_tab(self, tab_widget):
        """禁用标定tab（追踪已关闭）。
        
        Args:
            tab_widget: QTabWidget 实例
        """
        if self._calibration_tab_index is not None:
            tab_widget.setTabEnabled(self._calibration_tab_index, False)
    
    def get_calibration_widget(self):
        """获取标定widget。
        
        Returns:
            ViveTrackerCaliWidget 实例
        """
        return self._calibration_widget
    
    def get_calibration_tab_index(self):
        """获取标定tab索引。
        
        Returns:
            标定tab的索引
        """
        return self._calibration_tab_index
