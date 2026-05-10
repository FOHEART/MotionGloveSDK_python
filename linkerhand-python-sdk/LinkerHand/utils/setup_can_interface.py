#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAN Interface Automatic Setup Module
自动配置和启动 CAN 接口

Author: Auto-generated
Date: 2026-05-06
Description: 自动执行 CAN 接口初始化命令
"""

import sys
import os
import subprocess
import platform

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from color_msg import ColorMsg
from load_write_yaml import LoadWriteYaml


class SetupCANInterface:
    """CAN 接口自动设置类"""
    
    def __init__(self):
        """初始化 CAN 接口设置"""
        self.yaml = LoadWriteYaml()
        self.config = self.yaml.load_setting_yaml()
        self.password = self.config.get("PASSWORD", "")
        self.os_type = platform.system()
    
    def setup_can(self, can_interface="can0", bitrate=1000000):
        """
        自动设置 CAN 接口
        
        Args:
            can_interface (str): CAN 接口名称，默认 can0
            bitrate (int): CAN 比特率，默认 1000000
            
        Returns:
            bool: 设置成功返回 True，失败返回 False
        """
        
        # Windows 系统不需要设置
        if self.os_type == "Windows":
            ColorMsg(msg=f"Windows system detected, CAN interface setup skipped", color="yellow")
            return True
        
        # Linux 系统执行 CAN 配置
        if self.os_type == "Linux":
            return self._setup_can_linux(can_interface, bitrate)
        
        return False
    
    def _setup_can_linux(self, can_interface="can0", bitrate=1000000):
        """
        Linux 系统 CAN 接口配置
        
        Args:
            can_interface (str): CAN 接口名称
            bitrate (int): CAN 比特率
            
        Returns:
            bool: 设置成功返回 True
        """
        
        try:
            # 检查 CAN 接口是否已经启动
            result = subprocess.run(
                ["ip", "link", "show", can_interface],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and "state UP" in result.stdout:
                ColorMsg(msg=f"CAN interface '{can_interface}' is already up", color="green")
                return True
            
            # 使用 sudo 启动 CAN 接口
            ColorMsg(msg=f"Initializing CAN interface '{can_interface}'...", color="yellow")
            
            # 构建命令
            cmd = [
                "sudo",
                "/usr/sbin/ip",
                "link",
                "set",
                can_interface,
                "up",
                "type",
                "can",
                "bitrate",
                str(bitrate)
            ]
            
            # 尝试使用密码执行 sudo 命令
            if self.password:
                result = subprocess.run(
                    ["sudo", "-S"] + cmd[1:],
                    input=f"{self.password}\n",
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            else:
                # 如果没有密码，直接执行（假设已配置 sudoers）
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            
            if result.returncode == 0:
                ColorMsg(msg=f"CAN interface '{can_interface}' initialized successfully", color="green")
                return True
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                ColorMsg(
                    msg=f"Failed to initialize CAN interface: {error_msg}",
                    color="red"
                )
                return False
                
        except subprocess.TimeoutExpired:
            ColorMsg(msg="CAN interface setup timed out", color="red")
            return False
        except FileNotFoundError:
            ColorMsg(msg="/usr/sbin/ip command not found", color="red")
            return False
        except Exception as e:
            ColorMsg(msg=f"Error during CAN interface setup: {str(e)}", color="red")
            return False
    
    def verify_can_interface(self, can_interface="can0"):
        """
        验证 CAN 接口是否正常
        
        Args:
            can_interface (str): CAN 接口名称
            
        Returns:
            bool: 接口正常返回 True
        """
        
        if self.os_type == "Windows":
            return True
        
        try:
            # 检查 sysfs 接口状态
            interface_path = f"/sys/class/net/{can_interface}"
            if not os.path.exists(interface_path):
                ColorMsg(msg=f"CAN interface '{can_interface}' not found", color="red")
                return False
            
            # 读取接口状态
            operstate_path = os.path.join(interface_path, "operstate")
            if os.path.exists(operstate_path):
                with open(operstate_path, "r") as f:
                    state = f.read().strip()
                
                if state == "up":
                    ColorMsg(msg=f"CAN interface '{can_interface}' is UP", color="green")
                    return True
                else:
                    ColorMsg(msg=f"CAN interface '{can_interface}' is {state}", color="yellow")
                    return False
            
            return False
            
        except Exception as e:
            ColorMsg(msg=f"Error verifying CAN interface: {str(e)}", color="red")
            return False


def initialize_can_interface(can_interface="can0", bitrate=1000000, verify=True):
    """
    便捷函数：初始化 CAN 接口
    
    Args:
        can_interface (str): CAN 接口名称，默认 can0
        bitrate (int): CAN 比特率，默认 1000000
        verify (bool): 是否验证接口状态，默认 True
        
    Returns:
        bool: 初始化成功返回 True
        
    Usage:
        from LinkerHand.utils.setup_can_interface import initialize_can_interface
        initialize_can_interface()
    """
    
    setup = SetupCANInterface()
    
    # 执行设置
    if not setup.setup_can(can_interface, bitrate):
        return False
    
    # 验证接口
    if verify:
        return setup.verify_can_interface(can_interface)
    
    return True
