##
# @file hand_tracker_monitor.py
# @brief Real-time OpenVR hand tracker monitoring application
# @details 实时OpenVR手部追踪器监控应用程序
#          
#          功能 / Features:
#          - 读取hand_tracker_config.json配置文件 / Read hand_tracker_config.json
#          - 初始化OpenVR系统并发现设备 / Initialize OpenVR and discover devices
#          - 匹配序列号对应的追踪器 / Match trackers by serial number
#          - 实时显示手部位置和旋转数据 / Display real-time hand position and rotation
#          - 支持Ctrl+C、ESC、Q三种方式退出 / Support Ctrl+C, ESC, Q to exit
# 
# @usage
#   python hand_tracker_monitor.py [frequency_hz]
#   Example: python hand_tracker_monitor.py 30
# 
# @author Generated for MotionGloveSDK
# @version 1.0
##

import triad_openvr
import json
import time
import sys
import os
import threading

## @var exit_flag
#  @brief Global flag to control exit / 全局退出控制标志
#  @details 用于线程间通信以安全退出 / Used for thread-safe exit communication
exit_flag = False

## @fn listen_for_exit()
#  @brief Listen for exit signals from keyboard input
#  @details 监听键盘输入以接收退出信号
#           - 按ESC键退出 / Press ESC to exit
#           - 按Q或q键退出 / Press Q or q to exit
#           - 此函数运行在后台线程 / This function runs in background thread
#  @return None
def listen_for_exit():
    """Listen for ESC key or input to exit / 监听ESC或其他输入以退出"""
    global exit_flag
    try:
        while not exit_flag:
            # Simple stdin check - any input triggers exit
            char = sys.stdin.read(1)
            if char in ('\x1b', 'q', 'Q'):  # ESC, q, or Q
                exit_flag = True
                break
    except:
        pass

# Load hand tracker configuration / 加载手部追踪器配置
## @brief 从脚本同目录读取hand_tracker_config.json / Read config from script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, 'hand_tracker_config.json')

try:
    with open(config_path, 'r') as f:
        hand_config = json.load(f)  ##< @var hand_config 手部追踪器配置字典 / Hand tracker config dict
except FileNotFoundError:
    print(f"Error: hand_tracker_config.json not found at {config_path}")
    sys.exit(1)

# Initialize OpenVR system / 初始化OpenVR系统
## @brief 初始化OpenVR系统并发现设备 / Initialize OpenVR system and discover devices
v = triad_openvr.triad_openvr()  ##< @var v OpenVR系统实例 / OpenVR system instance
print("Available devices:")
v.print_discovered_objects()

# Build a mapping of serial numbers to device names / 建立序列号到设备名称的映射
## @brief 遍历所有发现的设备并建立映射表 / Traverse all discovered devices and build map
serial_to_device = {}  ##< @var serial_to_device 序列号→设备名称映射表 / Serial number → device name map
for device_name, device in v.devices.items():
    serial = device.get_serial().decode('utf-8') if isinstance(device.get_serial(), bytes) else device.get_serial()
    serial_to_device[serial] = device_name

print("\nSerial to Device Mapping:")
for serial, device_name in serial_to_device.items():
    print(f"  {serial} -> {device_name}")

# Find matched hand trackers / 匹配手部追踪器
## @brief 根据序列号匹配手部追踪器 / Match hand trackers by serial number
#  @details 比对配置文件中的序列号和发现的设备 / Match serial numbers from config with discovered devices
matched_trackers = {}  ##< @var matched_trackers 匹配成功的追踪器字典 / Matched trackers dictionary
for hand_name, config in hand_config.items():
    serial = config["SerialNumber"]
    if serial in serial_to_device:
        device_name = serial_to_device[serial]
        matched_trackers[hand_name] = {
            "serial": serial,
            "device_name": device_name,
            "device": v.devices[device_name]
        }
        print(f"\n✓ {hand_name} matched: {device_name} (Serial: {serial})")
    else:
        print(f"\n✗ {hand_name} NOT found (Serial: {serial})")

if not matched_trackers:
    print("\nError: No hand trackers matched!")
    sys.exit(1)

# Print tracking data / 打印追踪数据
## @brief 配置采样率和启动监控循环 / Configure sampling rate and start monitoring loop
print("\n" + "="*70)
print("Hand Tracker Position and Rotation Data")
print("Press Ctrl+C, ESC, or Q to exit")
print("="*70)

## @brief 解析命令行参数获取采样频率 / Parse command line args for sampling frequency
if len(sys.argv) == 1:
    interval = 1/60  ##< @var interval 采样间隔(秒) / Sampling interval (seconds) - Default 60 Hz
elif len(sys.argv) == 2:
    interval = 1/float(sys.argv[1])
else:
    print("Usage: python hand_tracker_monitor.py [frequency_hz]")
    sys.exit(1)

## @brief 启动后台线程监听退出信号 / Start background thread to listen for exit signals
listener_thread = threading.Thread(target=listen_for_exit, daemon=True)
listener_thread.start()

try:
    ## @section main_loop Main Monitoring Loop
    #  @brief 主监控循环 / Main monitoring loop
    #  @details 以指定频率持续读取和显示追踪器数据 / Continuously read and display tracker data at specified frequency
    while not exit_flag:
        start = time.time()
        
        ## @brief 打印当前时间戳 / Print current timestamp
        print(f"\n[{time.strftime('%H:%M:%S.%f')[:-3]}]")
        
        ## @brief 遍历所有匹配的追踪器并读取数据 / Iterate through all matched trackers and read data
        for hand_name, tracker_info in matched_trackers.items():
            device = tracker_info["device"]
            pose_euler = device.get_pose_euler()  ##< 获取欧拉角姿态 / Get Euler angle pose
            
            if pose_euler:
                x, y, z, yaw, pitch, roll = pose_euler
                print(f"\n{hand_name}:")
                print(f"  Position:  X={x:8.4f}m  Y={y:8.4f}m  Z={z:8.4f}m")
                print(f"  Rotation:  Yaw={yaw:7.2f}°  Pitch={pitch:7.2f}°  Roll={roll:7.2f}°")
            else:
                print(f"\n{hand_name}: Pose data not valid")
        
        ## @brief 控制循环时序以保持指定的采样频率 / Control loop timing to maintain specified frequency
        sleep_time = interval - (time.time() - start)
        if sleep_time > 0:
            time.sleep(sleep_time)

except KeyboardInterrupt:
    print("\n\nMonitoring stopped.")
    exit_flag = True
finally:
    ## @brief 清理资源并退出 / Clean up resources and exit
    exit_flag = True
    sys.exit(0)
