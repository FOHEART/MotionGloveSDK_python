#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动循环测试控制脚本
功能：自动打开CAN接口并调用joint_value_tester进行所有手指的循环测试
"""

import os
import sys
import time
import signal
import threading
from typing import List

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
target_dir = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.append(target_dir)
sys.path.append(current_dir)

from LinkerHand.linker_hand_api import LinkerHandApi
from LinkerHand.utils.load_write_yaml import LoadWriteYaml
from LinkerHand.utils.color_msg import ColorMsg
from LinkerHand.utils.setup_can_interface import initialize_can_interface
from src.joint_value_tester import JointValueTester


class ThreadBasedJointValueTester:
    """基于线程的关节值测试器 - 不依赖PyQt5，适合命令行使用"""
    
    def __init__(self, interval: float = 0.1):
        """
        初始化线程版测试器
        
        Args:
            interval: 更新间隔（秒），默认0.1秒（100ms）
        """
        self.is_testing = False
        self.values = [255] * 10  # 初始化为255
        self.direction = -1  # -1: 递减, 1: 递增
        self.interval = interval
        self.thread = None
        self.lock = threading.Lock()
    
    def start_test(self):
        """开始循环测试"""
        if not self.is_testing:
            self.is_testing = True
            self.values = [255] * 10
            self.direction = -1
            self.thread = threading.Thread(target=self._update_loop, daemon=True)
            self.thread.start()
    
    def stop_test(self):
        """停止循环测试"""
        if self.is_testing:
            self.is_testing = False
            if self.thread:
                self.thread.join(timeout=1)
    
    def _update_loop(self):
        """后台更新循环"""
        while self.is_testing:
            self._update_values()
            time.sleep(self.interval)
    
    def _update_values(self):
        """更新关节值 - 255到0循环"""
        with self.lock:
            current_val = self.values[0]
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
    
    def get_current_values(self) -> List[int]:
        """获取当前的值"""
        with self.lock:
            return self.values.copy()
    
    def is_running(self) -> bool:
        """检查测试是否正在运行"""
        return self.is_testing


class AutoLoopTestControl:
    """自动循环测试控制器"""
    
    def __init__(self, hand_type: str = "left", hand_joint: str = "L10", 
                 can_interface: str = "can0", bitrate: int = 1000000):
        """
        初始化自动循环测试控制器
        
        Args:
            hand_type: 手类型 "left" 或 "right"
            hand_joint: 手部型号 "L10", "L20" 等
            can_interface: CAN接口名称
            bitrate: CAN波特率
        """
        self.hand_type = hand_type
        self.hand_joint = hand_joint
        self.can_interface = can_interface
        self.bitrate = bitrate
        self.api = None
        self.tester = None
        self.is_running = False
        
        # 信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """处理中断信号"""
        ColorMsg(msg="收到中断信号，停止测试...", color="yellow")
        self.stop()
        sys.exit(0)
    
    def initialize(self) -> bool:
        """
        初始化系统
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 初始化CAN接口
            ColorMsg(msg=f"正在初始化CAN接口 {self.can_interface}...", color="yellow")
            if not initialize_can_interface(can_interface=self.can_interface, bitrate=self.bitrate):
                ColorMsg(msg="CAN接口初始化失败，但继续尝试...", color="yellow")
            
            # 加载配置
            ColorMsg(msg="正在加载配置文件...", color="yellow")
            config = LoadWriteYaml().load_setting_yaml()
            
            # 初始化灵巧手API
            ColorMsg(msg=f"正在初始化灵巧手 ({self.hand_type} {self.hand_joint})...", color="yellow")
            hand_type_upper = self.hand_type.upper()
            modbus_port = config["LINKER_HAND"].get(f"{hand_type_upper}_HAND", {}).get("MODBUS", "None")
            self.api = LinkerHandApi(
                hand_type=self.hand_type,
                hand_joint=self.hand_joint,
                can=self.can_interface,
                modbus=modbus_port
            )
            
            # 初始化测试器
            self.tester = ThreadBasedJointValueTester(interval=0.1)
            
            ColorMsg(msg="✓ 系统初始化成功！", color="green")
            return True
            
        except Exception as e:
            ColorMsg(msg=f"✗ 初始化失败: {str(e)}", color="red")
            return False
    
    def run(self, duration: int = None, loop_count: int = None):
        """
        运行循环测试
        
        Args:
            duration: 测试持续时间（秒），为None时无限循环
            loop_count: 循环次数，为None时无限循环，与duration互斥
        """
        if not self.api or not self.tester:
            ColorMsg(msg="✗ 系统未初始化", color="red")
            return
        
        self.is_running = True
        start_time = time.time()
        cycle_count = 0
        
        ColorMsg(msg=f"\n开始循环测试...", color="green")
        ColorMsg(msg=f"手部型号: {self.hand_type} {self.hand_joint}", color="green")
        if duration:
            ColorMsg(msg=f"测试持续时间: {duration}秒", color="green")
        elif loop_count:
            ColorMsg(msg=f"测试循环次数: {loop_count}次", color="green")
        else:
            ColorMsg(msg=f"持续运行，按 Ctrl+C 停止", color="green")
        ColorMsg(msg=f"\n", color="green")
        
        # 启动测试器
        self.tester.start_test()
        
        try:
            while self.is_running:
                # 检查是否达到持续时间
                if duration and (time.time() - start_time) > duration:
                    ColorMsg(msg=f"✓ 达到设定的持续时间 {duration}秒，测试完成", color="green")
                    break
                
                # 检查是否达到循环次数
                if loop_count and cycle_count >= loop_count:
                    ColorMsg(msg=f"✓ 完成 {loop_count}次循环，测试完成", color="green")
                    break
                
                # 获取当前测试值
                current_values = self.tester.get_current_values()
                
                # 发送给灵巧手
                try:
                    self.api.finger_move(pose=current_values)
                    
                    # 打印进度信息
                    elapsed = time.time() - start_time
                    value_str = ", ".join(f"{v:3d}" for v in current_values)
                    status_line = f"[{elapsed:6.1f}s] 循环 #{cycle_count:3d} | 值: [{value_str}]"
                    print(f"\r{status_line}", end="", flush=True)
                    
                except Exception as e:
                    ColorMsg(msg=f"\n✗ 发送命令失败: {str(e)}", color="red")
                    break
                
                # 等待100ms（与测试器同步）
                time.sleep(0.1)
                cycle_count += 1
                
        except KeyboardInterrupt:
            ColorMsg(msg=f"\n\n✓ 用户中断，停止测试", color="yellow")
        finally:
            self.stop()
    
    def stop(self):
        """停止测试"""
        self.is_running = False
        if self.tester:
            self.tester.stop_test()
        if self.api:
            try:
                self.api.shutdown()
            except:
                pass
        ColorMsg(msg="\n✓ 测试已停止", color="green")
    
    def test_with_duration(self, seconds: int):
        """
        运行指定时间的测试
        
        Args:
            seconds: 测试秒数
        """
        self.run(duration=seconds)
    
    def test_with_cycles(self, cycles: int):
        """
        运行指定循环次数的测试
        
        Args:
            cycles: 循环次数
        """
        self.run(loop_count=cycles)
    
    def test_infinite(self):
        """运行无限循环测试"""
        self.run(duration=None, loop_count=None)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="自动循环测试控制脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行10秒测试
  python3 auto_loop_test_control.py --duration 10
  
  # 运行100次循环测试
  python3 auto_loop_test_control.py --cycles 100
  
  # 无限循环测试（按Ctrl+C停止）
  python3 auto_loop_test_control.py
  
  # 测试右手L20
  python3 auto_loop_test_control.py --hand-type right --hand-joint L20
        """
    )
    
    parser.add_argument("--hand-type", default="left", choices=["left", "right"],
                        help="手类型 (默认: left)")
    parser.add_argument("--hand-joint", default="L10", 
                        choices=["O6", "L6", "L7", "L10", "L20", "L21", "L25", "G20"],
                        help="手部型号 (默认: L10)")
    parser.add_argument("--can-interface", default="can0",
                        help="CAN接口名称 (默认: can0)")
    parser.add_argument("--bitrate", type=int, default=1000000,
                        help="CAN波特率 (默认: 1000000)")
    parser.add_argument("--duration", type=int, default=None,
                        help="测试持续时间（秒）")
    parser.add_argument("--cycles", type=int, default=None,
                        help="测试循环次数")
    
    args = parser.parse_args()
    
    # 创建控制器
    controller = AutoLoopTestControl(
        hand_type=args.hand_type,
        hand_joint=args.hand_joint,
        can_interface=args.can_interface,
        bitrate=args.bitrate
    )
    
    # 初始化
    if not controller.initialize():
        sys.exit(1)
    
    # 运行测试
    try:
        if args.duration:
            ColorMsg(msg=f"运行 {args.duration} 秒的测试", color="cyan")
            controller.test_with_duration(args.duration)
        elif args.cycles:
            ColorMsg(msg=f"运行 {args.cycles} 次循环的测试", color="cyan")
            controller.test_with_cycles(args.cycles)
        else:
            ColorMsg(msg="运行无限循环测试", color="cyan")
            controller.test_infinite()
    except Exception as e:
        ColorMsg(msg=f"✗ 测试过程中出错: {str(e)}", color="red")
        sys.exit(1)


if __name__ == "__main__":
    main()
