"""@file  __init__.py
@brief  MotionGloveSDK Python 包（src）。
@details
模块地图（详见仓库根 AGENTS.md）：
  - motionGloveSDK.py      对外公共接口（与 C++ motionGloveSDK.h 同名）
  - native/                ctypes 转接层（唯一与 C++ 内存布局耦合的包）
  - definitions.py         数据结构与枚举（对应 C++ 头文件）
  - xsqeconverter.py       欧拉角 ↔ 四元数转换（xsQEConverter 移植）
  - decode_glove_csv.py    CSV body → GloveFrame 解析（回放/调试用）
  - glove_frame_assembler.py   UDP 分包拼接（C++ GloveSplitFrameMgr 参考实现）
  - csv_frame_reader.py    CSV 导出文件逐帧读取（回放）
  - csv_to_bvh.py / bvh_to_fbx.py   动作数据格式转换
  - config_io.py           config.json 原子读写
  - port_occupier.py       UDP 端口占用进程探测
  - blender_path_detector.py / boot_mode_dialog.py / translator_helper.py
                           GUI 工具层（PySide6 / Blender 相关）

测试位于 tests/unit/（pytest，纯 Python，不依赖原生库与 GUI）。
"""
