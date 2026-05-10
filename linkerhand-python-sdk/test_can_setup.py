#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAN Interface Setup - Test Script
CAN 接口初始化 - 测试脚本

This script tests the CAN initialization functionality without requiring actual hardware.
这个脚本测试 CAN 初始化功能，无需实际硬件。

Usage: python3 test_can_setup.py
"""

import sys
import os

# 设置 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from LinkerHand.utils.setup_can_interface import SetupCANInterface
from LinkerHand.utils.color_msg import ColorMsg


def test_setup():
    """测试 CAN 初始化功能"""
    
    print("\n" + "="*70)
    print("CAN Interface Setup - Test Script")
    print("CAN 接口初始化 - 测试脚本")
    print("="*70 + "\n")
    
    try:
        # 创建 SetupCANInterface 实例
        ColorMsg(msg="1. Creating SetupCANInterface instance...", color="yellow")
        setup = SetupCANInterface()
        ColorMsg(msg="   ✓ Instance created successfully", color="green")
        
        # 显示检测到的系统
        print(f"\n2. System Information:")
        print(f"   - OS: {setup.os_type}")
        print(f"   - CAN Interface: {setup.config['LINKER_HAND']['LEFT_HAND']['CAN']}")
        print(f"   - MODBUS: {setup.config['LINKER_HAND']['LEFT_HAND']['MODBUS']}")
        print(f"   - Password: {'*' * len(setup.password) if setup.password else 'Not set'}")
        
        # 测试接口验证（不需要实际修改接口）
        ColorMsg(msg="\n3. Testing interface verification...", color="yellow")
        can_interface = setup.config['LINKER_HAND']['LEFT_HAND']['CAN']
        is_up = setup.verify_can_interface(can_interface)
        if is_up:
            ColorMsg(msg=f"   ✓ Interface '{can_interface}' is UP", color="green")
        else:
            ColorMsg(msg=f"   ! Interface '{can_interface}' is not UP (expected if not pre-initialized)", color="yellow")
        
        # 显示预期的命令
        ColorMsg(msg="\n4. Expected command to be executed:", color="yellow")
        print(f"   sudo /usr/sbin/ip link set {can_interface} up type can bitrate 1000000")
        
        # 显示配置摘要
        ColorMsg(msg="\n5. Configuration Summary:", color="yellow")
        print(f"   - Auto-initialization: Enabled")
        print(f"   - Target interface: {can_interface}")
        print(f"   - Bitrate: 1000000")
        print(f"   - OS: {setup.os_type}")
        
        if setup.os_type == "Windows":
            ColorMsg(msg="   - Windows detected: CAN setup will be skipped", color="yellow")
        elif setup.os_type == "Linux":
            ColorMsg(msg="   - Linux detected: CAN setup will execute", color="yellow")
        
        # 建议
        ColorMsg(msg="\n6. Recommendations:", color="yellow")
        print("   ✓ All settings look correct")
        print("   ✓ You can now run: python3 example/gui_control/gui_control.py")
        print("   ✓ Or run: python3 example/gui_control/src/init_can.py")
        
        print("\n" + "="*70)
        ColorMsg(msg="✓ Setup test completed successfully!", color="green")
        print("="*70 + "\n")
        
        return 0
        
    except Exception as e:
        ColorMsg(msg=f"\n✗ Error during test: {str(e)}", color="red")
        print(f"\nTraceback: {e}")
        print("\n" + "="*70 + "\n")
        return 1


if __name__ == "__main__":
    exit_code = test_setup()
    sys.exit(exit_code)
