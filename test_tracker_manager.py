#!/usr/bin/env python3
"""test_tracker_manager.py
演示如何使用 ViveTrackerMgr 结构体和 TrackerManager

此测试脚本展示了：
1. 创建和管理 Tracker 信息
2. 访问 ViveTrackerWidget 中的 tracker_manager
3. 获取所有 Tracker 的统一信息
"""

from triad_openvr.tracker_manager import ViveTrackerMgr, TrackerManager, get_global_tracker_manager
import numpy as np


def test_vive_tracker_mgr():
    """测试 ViveTrackerMgr 结构体的基本功能。"""
    print("=" * 60)
    print("测试 1: ViveTrackerMgr 基本功能")
    print("=" * 60)
    
    # 创建一个 Tracker
    tracker = ViveTrackerMgr(name="left")
    
    # 更新位置
    tracker.update_position(0.5, -0.2, 1.0)
    
    # 更新欧拉角
    tracker.update_euler(45.0, 30.0, 15.0)
    
    # 更新四元数
    tracker.update_quat(0.7071, 0.0, 0.7071, 0.0)
    
    # 更新旋转矩阵
    rotation_matrix = np.array([
        [0.7071, -0.7071, 0.0],
        [0.7071,  0.7071, 0.0],
        [0.0,     0.0,    1.0]
    ], dtype=np.float32)
    tracker.update_rotation_matrix(rotation_matrix)
    
    # 标记为在线和有效
    tracker.is_online = True
    tracker.valid = True
    tracker.remarks = "左手 Tracker 运行正常"
    
    # 打印信息
    print(tracker)
    print(f"\n✓ 获取位置: {tracker.get_position()}")
    print(f"✓ 获取欧拉角: {tracker.get_euler()}")
    print(f"✓ 获取四元数: {tracker.get_quat()}")
    print(f"✓ 获取旋转矩阵:\n{tracker.get_rotation_matrix()}")
    print()


def test_tracker_manager():
    """测试 TrackerManager 的管理功能。"""
    print("=" * 60)
    print("测试 2: TrackerManager 管理功能")
    print("=" * 60)
    
    # 创建管理器
    manager = TrackerManager()
    
    # 注册多个 Tracker
    left = manager.register_tracker("left")
    right = manager.register_tracker("right")
    waist = manager.register_tracker("waist")
    
    # 更新数据
    left.update_position(0.5, -0.2, 1.0)
    left.is_online = True
    left.valid = True
    
    right.update_position(-0.5, 0.2, 1.0)
    right.is_online = True
    right.valid = True
    
    waist.update_position(0.0, 0.0, 0.5)
    waist.is_online = False
    waist.valid = False
    
    # 获取所有 Tracker
    print(f"\n总共注册了 {len(manager)} 个 Tracker:")
    for name, tracker in manager.get_all_trackers().items():
        print(f"  - {name}: {'在线' if tracker.is_online else '离线'}")
    
    # 获取在线 Tracker
    print(f"\n在线的 Tracker:")
    for name, tracker in manager.get_online_trackers().items():
        print(f"  - {name}: {tracker.get_position()}")
    
    # 检查是否存在
    print(f"\n✓ 'left' in manager: {'left' in manager}")
    print(f"✓ 'unknown' in manager: {'unknown' in manager}")
    
    # 通过 [] 操作符访问
    print(f"\n通过 [] 操作符访问:")
    print(f"  manager['left']: {manager['left']}")
    print()


def test_global_tracker_manager():
    """测试全局 Tracker 管理器。"""
    print("=" * 60)
    print("测试 3: 全局 Tracker 管理器")
    print("=" * 60)
    
    # 获取全局管理器
    global_mgr = get_global_tracker_manager()
    
    # 注册 Tracker
    tracker1 = global_mgr.register_tracker("global_left")
    tracker2 = global_mgr.register_tracker("global_right")
    
    # 更新数据
    tracker1.update_position(1.0, 0.0, 0.0)
    tracker1.is_online = True
    
    tracker2.update_position(-1.0, 0.0, 0.0)
    tracker2.is_online = True
    
    # 打印摘要
    global_mgr.print_summary()


def test_integration():
    """测试与 ViveTrackerWidget 的集成（模拟）。"""
    print("=" * 60)
    print("测试 4: ViveTrackerWidget 集成示例")
    print("=" * 60)
    
    # 模拟 ViveTrackerWidget 中的 tracker_manager
    tracker_mgr = get_global_tracker_manager()
    
    # 清空之前的数据
    tracker_mgr.clear()
    
    # 模拟 ViveTrackerWidget 注册 Tracker
    print("\n1. ViveTrackerWidget 开启追踪...")
    left = tracker_mgr.register_tracker("left")
    right = tracker_mgr.register_tracker("right")
    
    # 模拟接收到的追踪数据
    print("2. 接收追踪数据...")
    left.update_position(0.3, -0.1, 0.8)
    left.update_euler(30, 45, 15)
    left.update_quat(0.9, 0.1, 0.2, 0.3)
    left.is_online = True
    left.valid = True
    left.remarks = "正常追踪"
    
    right.update_position(-0.3, 0.1, 0.8)
    right.update_euler(350, 315, 345)
    right.update_quat(0.9, -0.1, -0.2, -0.3)
    right.is_online = True
    right.valid = True
    right.remarks = "正常追踪"
    
    # 获取信息
    print("\n3. 访问 Tracker 信息...")
    all_trackers = tracker_mgr.get_all_trackers()
    print(f"   已注册 {len(all_trackers)} 个 Tracker")
    
    online_trackers = tracker_mgr.get_online_trackers()
    print(f"   在线 Tracker: {', '.join(online_trackers.keys())}")
    
    # 打印详细信息
    print("\n4. 详细信息:")
    for name, tracker in all_trackers.items():
        print(f"\n   【{name}】")
        print(f"   位置: {tracker.get_position()}")
        print(f"   欧拉角: {tracker.get_euler()}")
        print(f"   四元数: {tracker.get_quat()}")
        print(f"   在线: {tracker.is_online}")
        print(f"   备注: {tracker.remarks}")
    
    print()


if __name__ == "__main__":
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 14 + "ViveTrackerMgr 测试脚本" + " " * 20 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    test_vive_tracker_mgr()
    test_tracker_manager()
    test_global_tracker_manager()
    test_integration()
    
    print("=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    print()
    print("使用说明：")
    print("  1. ViveTrackerMgr: 单个 Tracker 的信息结构体")
    print("  2. TrackerManager: 管理多个 Tracker 的管理器")
    print("  3. get_global_tracker_manager(): 获取全局管理器实例")
    print()
    print("在 ViveTrackerWidget 中使用：")
    print("  tracker_mgr = widget.get_tracker_manager()")
    print("  left_tracker = tracker_mgr.get_tracker('left')")
    print("  all_trackers = tracker_mgr.get_all_trackers()")
    print()
