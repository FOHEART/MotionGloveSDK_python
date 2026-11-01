# Changelog

## [Unreleased]

### Added
- **C++ 原生数据流后端**（`third_party/MotionGloveSDK_cpp`，git submodule）：UDP 接收、分包重组、CSV 解析与帧缓存全部改由 C++ SDK 编译出的 `MotionGloveSDK.dll` / `libMotionGloveSDK.so` 完成，Python 不再解析数据流。
- **Python 转接层**（`src/native/`）：`abi.py`（ctypes 结构体，唯一与 C++ 内存布局耦合的文件）、`loader.py`（库定位与导出函数绑定）、`mapper.py`（原生结构体 → `GloveFrame`）、`backend.py`（`NativeBackend` 稳定接口）、`errors.py`（`MotionGloveNativeError` / `NativeLibraryNotFound`）。C++ 工程改动时只需维护该目录。
- **原生库构建脚本**：`scripts/[Windows]build_mgsdk_cpp.cmd`、`scripts/[Linux]build_mgsdk_cpp.sh`，产物安装到 `build/mgsdk_cpp/install/`；支持环境变量 `MOTIONGLOVE_NATIVE_LIB` 指定库文件。
- **ABI 校验工具**：`scripts/abi_probe.cpp` + `scripts/verify_native_abi.py`，编译探针打印 C++ 侧 `sizeof/offsetof` 并与 `src/native/abi.py` 逐项比对。
- **原生后端冒烟测试**：`scripts/native_smoke_test.py`，向本机 UDP 端口发送合成 42/32 段数据帧并逐项校验（无需真实手套）。
- 新增公共接口：`MotionGloveSDK_GetSkeletonsFrameType()`、`MotionGloveSDK_IsAvailable()`、`MotionGloveSDK_GetBackendName()`、`MotionGloveSDK_GetNativeLibraryPath()`。
- **CI 作业 `native-backend`**：checkout submodule + 编译 C++ 库 + ABI 校验 + 冒烟测试（Windows / Ubuntu 24.04）。
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

### Fixed
- **`src/csv_to_bvh.py` BVH 骨骼首尾脱节**：手指关节错误使用 6 通道（含位置），导致 Blender 等工具在父骨骼旋转后子骨骼位置错位。修复：手指关节改为 3 通道（仅旋转），骨骼方向完全由 HIERARCHY OFFSET 定义；RightHand / LeftHand 根节点保留 6 通道。

### Changed
- **仓库目录整理**：`CLAUDE.md` 更名为 `AGENTS.md`；`fonts/`、`csvPlayer/`、`docs/`、`MotionGloveBVH/`、`triad_openvr/`、`CSV_PLAYBACK_UserManual.md/.pdf` 统一移入 `tools/`；示例程序、PyInstaller spec、README 与手册内的相对路径同步更新。
- `src/motionGloveSDK.py`：改为对 `src/native` 的薄门面，函数名与返回值语义保持不变；原生库不可用时抛 `MotionGloveNativeError`（`MotionGloveSDK_ListenUDPPort` 仍以 `-1` 表示失败）。
- `src/glove_frame_assembler.py`、`src/decode_glove_csv.py`：不再参与 UDP 数据流路径，仅保留给 `motionGloveSDK_rawReceiver.py`（原始数据调试）与 CSV 回放使用。
- `MotionGlove3DViewer.spec`：打包时自动收集 `MotionGloveSDK` 原生库（缺失时打包直接失败）；`src/native/loader.py` 增加 PyInstaller 冻结环境的库查找路径。
- `motionGloveSDK_example3_3dView.py`：轮询线程与左侧面板在原生库不可用时不再崩溃，改为提示编译指引。
- `scripts/[Windows]git_pull_latest.cmd`、`scripts/[Linux]git_pull_latest.sh`：拉取代码后自动同步 submodule 并重新编译原生库。
- **末梢虚拟骨骼移除**：删除固定长度末梢骨骼合成逻辑（`FINGERTIP_BONE_LENGTH`、`_FINGERTIP_BONES`、`_fingertip_actors` 及 `_on_timer` 中的四元数 Y 轴投影代码），改由发送端传入的真实 `*3End` 骨骼位置替代。
- `src/decode_glove_csv.py`：骨骼计数从 `KHHS32_SKELETON_COUNT` 更新为 `KHHS42_SKELETON_COUNT`，支持 42 骨骼帧的解析；欧拉角转四元数改用 `src/xsqeconverter.py`，移除对旧 `euler_to_quat.py` 的依赖。
- `_BONE_LINKS`：从 30 条扩展至 40 条，新增 10 条 `*3 → *3End` 末梢连线；`_BONE_PARENT` 自动由 `_BONE_LINKS` 派生，覆盖全部 42 骨骼。
- `python_draw3d/draw_config_io.py`：骨骼连线默认粗细从 2 调整为 10；`DrawConfigWidget` 连线粗细 Slider 最大值从 20 扩展至 30。
- **世界坐标轴大小**：`add_axes_to_renderer` 调用时 `length` 从 0.05 缩减至 0.025（缩小一半）。
- `src/euler_to_quat.py` 已删除，功能统一由 `src/xsqeconverter.py` 提供。


