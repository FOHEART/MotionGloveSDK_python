#!/usr/bin/env python3
"""测试 VR Tracker 模型网格简化功能。

演示不同简化比率下的面数减少效果。
"""

import sys
from pathlib import Path

# 添加 triad_openvr 到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from triad_openvr.vr_tracker_model_loader import VRTrackerModelActor
    
    print("=" * 80)
    print("VR Tracker 模型网格简化演示")
    print("=" * 80)
    print()
    
    # 测试不同的简化比率
    test_configs = [
        ("不简化（100% 保留）", False, 1.0),
        ("极致简化（保留 10%）", True, 0.1),
        ("激进简化（保留 20%）", True, 0.2),
        ("平衡简化（保留 50%）", True, 0.5),
        ("轻度简化（保留 75%）", True, 0.75),
    ]
    
    for config_name, enable_decimation, reduction_ratio in test_configs:
        print(f"\n{'─' * 80}")
        print(f"配置：{config_name}")
        print(f"{'─' * 80}")
        
        try:
            # 创建模型 Actor
            actor = VRTrackerModelActor(
                enable_decimation=enable_decimation,
                reduction_ratio=reduction_ratio
            )
            
            # 获取面数统计
            info = actor.get_face_count_info()
            
            print(f"\n面数统计：")
            print(f"  原始面数：      {info['original']} 个")
            print(f"  最终面数：      {info['final']} 个")
            print(f"  减少面数：      {info['reduced']} 个")
            print(f"  减少比例：      {info['reduction_percent']:.1f}%")
            print(f"  保留比例：      {100 - info['reduction_percent']:.1f}%")
            
        except Exception as e:
            print(f"  ✗ 错误：{e}")
    
    print()
    print("=" * 80)
    print("演示完成")
    print("=" * 80)
    print()
    print("使用建议：")
    print("  • 根据需要调整 reduction_ratio 参数以平衡性能和显示质量")
    print("  • 推荐使用 reduction_ratio = 0.3-0.5 获得良好的性能/质量比")
    print("  • enable_decimation = False 可禁用简化，加载原始模型")
    print()
    
except ImportError as e:
    print(f"✗ 导入失败：{e}")
    print("请确保 VTK 已正确安装到 libs/ 目录")
    sys.exit(1)
except Exception as e:
    print(f"✗ 测试失败：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
