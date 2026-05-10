#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAN Interface Setup Script
CAN 接口自动初始化脚本

这个脚本可以单独运行，用于初始化 CAN 接口
Before running any LinkerHand application on Linux, you can run this script first:
    python3 src/init_can.py

Author: Auto-generated
Date: 2026-05-06
"""

import sys
import os

# 设置 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
target_dir = os.path.abspath(os.path.join(current_dir, "../../.."))
sys.path.append(target_dir)

from LinkerHand.utils.setup_can_interface import initialize_can_interface, SetupCANInterface
from LinkerHand.utils.color_msg import ColorMsg
from LinkerHand.utils.load_write_yaml import LoadWriteYaml


def main():
    """主函数"""
    
    print("\n" + "="*60)
    print("CAN Interface Initialization Script")
    print("CAN 接口初始化脚本")
    print("="*60 + "\n")
    
    try:
        # 获取配置
        yaml = LoadWriteYaml()
        config = yaml.load_setting_yaml()
        
        # 显示当前配置
        can_interface = config['LINKER_HAND']['LEFT_HAND']['CAN']
        modbus = config['LINKER_HAND']['LEFT_HAND']['MODBUS']
        
        ColorMsg(msg=f"Current configuration:", color="yellow")
        ColorMsg(msg=f"  CAN Interface: {can_interface}", color="yellow")
        ColorMsg(msg=f"  MODBUS: {modbus}", color="yellow")
        
        # 如果使用 MODBUS RS485，跳过 CAN 初始化
        if modbus != "None":
            ColorMsg(msg=f"\nRS485 (MODBUS) mode detected, CAN initialization skipped.", color="yellow")
            ColorMsg(msg=f"To use RS485: grant permissions with: sudo chmod 777 {modbus}", color="yellow")
            return 0
        
        # 初始化 CAN 接口
        ColorMsg(msg=f"\nInitializing CAN interface '{can_interface}'...", color="yellow")
        print()
        
        success = initialize_can_interface(
            can_interface=can_interface,
            bitrate=1000000,
            verify=True
        )
        
        print()
        if success:
            ColorMsg(msg="✓ CAN interface initialized successfully!", color="green")
            ColorMsg(msg="You can now run LinkerHand applications.", color="green")
            return 0
        else:
            ColorMsg(msg="✗ CAN interface initialization failed!", color="red")
            ColorMsg(msg="Try running with: sudo python3 src/init_can.py", color="yellow")
            return 1
            
    except Exception as e:
        ColorMsg(msg=f"Error: {str(e)}", color="red")
        return 1
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
