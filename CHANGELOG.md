# Changelog

## [Unreleased]

### Added
- **42骨骼骨架支持**（`src/definitions.py`）：`BoneIndex` 枚举从 32 扩展至 42 个成员，新增 10 个末梢节点骨骼（`RightHandThumb3End` … `LeftHandPinky3End`），索引 4–41 按手指链顺序排列；`KHHS42_SKELETON_COUNT = 42`（旧 `KHHS32_SKELETON_COUNT = 32` 保留为兼容别名）；`BONE_NAMES` / `BONE_NAMES_SHORT` 同步扩展至 42 项。
- **末梢节点关节球渲染**（`motionGloveSDK_example3_3dView.py`）：10 个 `*3End` 骨骼以真实世界坐标位置渲染为关节球，不显示局部坐标轴；每个末梢节点与其父骨骼（`*3`）之间绘制骨骼连线，与其他骨骼连线渲染方式完全一致。
- `_END_BONE_INDICES`：模块级集合，由名称以 `End` 结尾的 `BoneIndex` 成员自动构建，驱动渲染循环中末梢节点的仅位置渲染分支。
- **PyInstaller 打包脚本**（`scripts/[Windows]build_dist.cmd`、`scripts/[Linux]build_dist.sh`）：一键将 `motionGloveSDK_example3_3dView.py` 打包为独立可执行文件，输出至 `dist/`；默认不显示终端窗口，通过 `--console` 参数启用；包含 VTK、PySide6、字体、UI 文件等所有运行时资源。
- `src/xsqeconverter.py`：欧拉角 ↔ 四元数转换模块，移植自 Movella `xsqeconverter.cpp`，支持全部 6 种旋转顺序（`XYZ/XZY/YXZ/YZX/ZXY/ZYX`）；提供 `euler_degree_to_quat_xyzw`、`euler_degree_to_quat_wxyz`、`quat_to_euler_degree` 三个接口。
- `src/csv_frame_reader.py`：`CsvFrameReader` 类，打开文件时预加载全部帧到内存（`list[GloveFrame]`），支持 `next_frame()`、`seek(index)`、`at_end`、`total_frames` 接口；解析器内置 `_EMBEDDED_HEADER_RE` 正则，兼容新版固件在同一行嵌入多个子包头的 CSV 格式。
- `ui/csv_import_widget.py`：`CsvImportWidget`，CSV 回放模式左侧面板；含文件选择、帧率下拉（10/24/30/60 Hz）、播放/暂停/重置按钮、帧号标签和进度条拖拽跳转。
- `CSV_PLAYBACK_UserManual.md`：面向最终用户的 CSV 回放操作说明文档。
- **AppMode 双启动模式**（`motionGloveSDK_example3_3dView.py`）：新增 `AppMode.CSV_PLAYBACK` 模式，通过顶部 `APP_MODE` 常量切换；CSV 回放使用单定时器架构（`time.monotonic()` 驱动），消除双定时器帧率抖动问题。
- **地平面默认显示**：`build_ground_plane_actor` 返回的地平面 Actor 初始可见性改为 `True`。

### Changed
- **末梢虚拟骨骼移除**：删除固定长度末梢骨骼合成逻辑（`FINGERTIP_BONE_LENGTH`、`_FINGERTIP_BONES`、`_fingertip_actors` 及 `_on_timer` 中的四元数 Y 轴投影代码），改由发送端传入的真实 `*3End` 骨骼位置替代。
- `src/decode_glove_csv.py`：骨骼计数从 `KHHS32_SKELETON_COUNT` 更新为 `KHHS42_SKELETON_COUNT`，支持 42 骨骼帧的解析；欧拉角转四元数改用 `src/xsqeconverter.py`，移除对旧 `euler_to_quat.py` 的依赖。
- `_BONE_LINKS`：从 30 条扩展至 40 条，新增 10 条 `*3 → *3End` 末梢连线；`_BONE_PARENT` 自动由 `_BONE_LINKS` 派生，覆盖全部 42 骨骼。
- `python_draw3d/draw_config_io.py`：骨骼连线默认粗细从 2 调整为 10；`DrawConfigWidget` 连线粗细 Slider 最大值从 20 扩展至 30。
- **世界坐标轴大小**：`add_axes_to_renderer` 调用时 `length` 从 0.05 缩减至 0.025（缩小一半）。
- `src/euler_to_quat.py` 已删除，功能统一由 `src/xsqeconverter.py` 提供。


