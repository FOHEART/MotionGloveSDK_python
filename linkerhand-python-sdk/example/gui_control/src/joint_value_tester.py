#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关节值测试模块
用于测试GUI中的关节值循环
每隔100毫秒将10个值循环变化：255->0->255->0...
"""

from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from typing import List


class JointValueTester(QObject):
    """关节值测试器 - 循环生成测试数据"""
    
    # 定义信号：当测试数据更新时发出
    values_updated = pyqtSignal(list)  # 发出更新的10个值
    test_status_changed = pyqtSignal(str)  # 测试状态改变
    
    def __init__(self):
        super().__init__()
        self.is_testing = False
        self.values = [0] * 10  # 初始化10个值为0
        self.direction = 1  # 1: 递增, -1: 递减
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_values)
        self.timer.setInterval(100)  # 每100毫秒更新一次
    
    def start_test(self):
        """开始循环测试"""
        if not self.is_testing:
            self.is_testing = True
            self.values = [255] * 10  # 初始值为255
            self.direction = -1  # -1: 递减开始
            self.timer.start()
            self.test_status_changed.emit("循环测试已启动")
    
    def stop_test(self):
        """停止循环测试"""
        if self.is_testing:
            self.is_testing = False
            self.timer.stop()
            self.test_status_changed.emit("循环测试已停止")
    
    def update_values(self):
        """更新关节值 - 0到255循环"""
        # 获取当前值
        current_val = self.values[0]
        
        # 更新值的方向
        new_val = current_val + self.direction
        
        # 检查边界并改变方向
        if new_val >= 255:
            new_val = 255
            self.direction = -1
        elif new_val <= 0:
            new_val = 0
            self.direction = 1
        
        # 更新所有10个值为相同的值
        self.values = [new_val] * 10
        
        # 发送更新信号
        self.values_updated.emit(self.values.copy())
    
    def get_current_values(self) -> List[int]:
        """获取当前的值"""
        return self.values.copy()
    
    def is_running(self) -> bool:
        """检查测试是否正在运行"""
        return self.is_testing
