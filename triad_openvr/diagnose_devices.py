#!/usr/bin/env python3
"""
ViveTracker 设备诊断工具

帮助用户查看系统中所有 OpenVR 设备的实际序列号，以便正确配置根目录 config.json
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def diagnose_devices():
    """诊断系统中的设备。"""
    print("=" * 60)
    print("ViveTracker 设备诊断工具")
    print("=" * 60)
    print()
    
    try:
        from triad_openvr.triad_openvr import triad_openvr
        
        print("[1] 初始化 OpenVR 系统...")
        system = triad_openvr()
        print("[✓] OpenVR 系统初始化成功")
        print()
        
        print("[2] 扫描系统设备...")
        devices = system.devices
        print(f"[✓] 找到 {len(devices)} 个设备")
        print()
        
        print("[3] 设备详细信息：")
        print("-" * 60)
        
        trackers = {}
        
        for device_name, device in devices.items():
            try:
                serial = device.get_serial()
                if isinstance(serial, bytes):
                    serial = serial.decode('utf-8')
                
                device_type = "未知"
                if "hmd" in device_name:
                    device_type = "HMD (头显)"
                elif "tracker" in device_name:
                    device_type = "Tracker (追踪器)"
                elif "tracking_reference" in device_name:
                    device_type = "Base Station (基站)"
                
                print(f"设备名称: {device_name}")
                print(f"设备类型: {device_type}")
                print(f"序列号:   {serial}")
                print()
                
                # 保存追踪器信息
                if "tracker" in device_name:
                    trackers[device_name] = serial
            except Exception as e:
                print(f"设备名称: {device_name}")
                print(f"错误: 无法读取设备信息 - {e}")
                print()
        
        print("-" * 60)
        print()
        
        if trackers:
            print("[4] 追踪器设备：")
            print("请将以下信息复制到项目根目录 config.json 中：")
            print()
            print("{")
            print('  "LeftHandTracker": {')
            print(f'    "SerialNumber": "{list(trackers.values())[0] if trackers else ""}"')
            print("  },")
            print('  "RightHandTracker": {')
            print(f'    "SerialNumber": "{list(trackers.values())[1] if len(trackers) > 1 else ""}"')
            print("  }")
            print("}")
            print()
        else:
            print("[⚠] 警告：系统中未找到追踪器设备！")
            print("请检查：")
            print("  1. 传感器是否已启动电源")
            print("  2. 传感器是否正确连接到基站")
            print("  3. SteamVR 服务是否正在运行")
            print()
        
        print("[✓] 诊断完成")
        
    except Exception as e:
        print(f"[✗] 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    diagnose_devices()
