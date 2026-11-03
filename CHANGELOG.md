# Changelog

## [Unreleased]

### Added
- **客户分发包打包脚本**：`scripts/package_for_customer.ps1`（包装：`scripts/package_for_customer.cmd`，cmd / sh 双解释器），生成 `MotionGloveSDK_python_v<版本号>.zip`。自动剔除 `.git`（含子模块 gitlink）、`.gitmodules`、`.github/`、`*git_pull_latest*` 脚本与内部资料/依赖缓存/构建产物，改写包内 README 中的 submodule 说明与 `config.json` 的本机路径，并在压缩前全文扫描确认没有 git 命令或仓库地址残留。
- **C++ 原生数据流后端**（`third_party/MotionGloveSDK_cpp`，git submodule）：UDP 接收、分包重组、CSV 解析与帧缓存全部改由 C++ SDK 编译出的 `MotionGloveSDK.dll` / `libMotionGloveSDK.so` 完成，Python 不再解析数据流。
- **Python 转接层**（`src/native/`）：`abi.py`（ctypes 结构体，唯一与 C++ 内存布局耦合的文件）、`loader.py`（库定位与导出函数绑定）、`mapper.py`（原生结构体 → `GloveFrame`）、`backend.py`（`NativeBackend` 稳定接口）、`errors.py`（`MotionGloveNativeError` / `NativeLibraryNotFound`）。C++ 工程改动时只需维护该目录。
- **原生库构建脚本**：`scripts/build_mgsdk_cpp.cmd`（cmd / sh 双解释器，同一份文件双平台可跑），产物安装到 `build/mgsdk_cpp/install/`；支持环境变量 `MOTIONGLOVE_NATIVE_LIB` 指定库文件。
- **ABI 校验工具**：`scripts/abi_probe.cpp` + `scripts/verify_native_abi.py`，编译探针打印 C++ 侧 `sizeof/offsetof` 并与 `src/native/abi.py` 逐项比对。
- **原生后端冒烟测试**：`scripts/native_smoke_test.py`，向本机 UDP 端口发送合成 42/32 段数据帧并逐项校验（无需真实手套）。
- 新增公共接口：`MotionGloveSDK_GetSkeletonsFrameType()`、`MotionGloveSDK_IsAvailable()`、`MotionGloveSDK_GetBackendName()`、`MotionGloveSDK_GetNativeLibraryPath()`。
- **CI 作业 `native-backend`**：checkout submodule + 编译 C++ 库 + ABI 校验 + 冒烟测试（Windows / Ubuntu 24.04）。
- **42骨骼骨架支持**（`src/definitions.py`）：`BoneIndex` 枚举从 32 扩展至 42 个成员，新增 10 个末梢节点骨骼（`RightHandThumb3End` … `LeftHandPinky3End`），索引 4–41 按手指链顺序排列；`KHHS42_SKELETON_COUNT = 42`（旧 `KHHS32_SKELETON_COUNT = 32` 保留为兼容别名）；`BONE_NAMES` / `BONE_NAMES_SHORT` 同步扩展至 42 项。
- **末梢节点关节球渲染**（`motionGloveSDK_example3_3dView.py`）：10 个 `*3End` 骨骼以真实世界坐标位置渲染为关节球，不显示局部坐标轴；每个末梢节点与其父骨骼（`*3`）之间绘制骨骼连线，与其他骨骼连线渲染方式完全一致。
- `_END_BONE_INDICES`：模块级集合，由名称以 `End` 结尾的 `BoneIndex` 成员自动构建，驱动渲染循环中末梢节点的仅位置渲染分支。
- **PyInstaller 一条龙打包脚本**（`build.cmd`，根目录，cmd / sh 双解释器）：安装 Python 依赖 → 编译原生库 → PyInstaller 打包，产物输出至 `dist/`；默认不显示终端窗口，通过 `--console` 参数启用；支持 `--force` / `--skip-deps` / `--skip-native` 控制各步骤。Windows 与 Linux/macOS 共用同一份文件。
- `src/xsqeconverter.py`：欧拉角 ↔ 四元数转换模块，移植自 Movella `xsqeconverter.cpp`，支持全部 6 种旋转顺序（`XYZ/XZY/YXZ/YZX/ZXY/ZYX`）；提供 `euler_degree_to_quat_xyzw`、`euler_degree_to_quat_wxyz`、`quat_to_euler_degree` 三个接口。
- `src/csv_frame_reader.py`：`CsvFrameReader` 类，打开文件时预加载全部帧到内存（`list[GloveFrame]`），支持 `next_frame()`、`seek(index)`、`at_end`、`total_frames` 接口；解析器内置 `_EMBEDDED_HEADER_RE` 正则，兼容新版固件在同一行嵌入多个子包头的 CSV 格式。
- `ui/csv_import_widget.py`：`CsvImportWidget`，CSV 回放模式左侧面板；含文件选择、帧率下拉（10/24/30/60 Hz）、播放/暂停/重置按钮、帧号标签和进度条拖拽跳转。
- `CSV_PLAYBACK_UserManual.md`：面向最终用户的 CSV 回放操作说明文档。
- **AppMode 双启动模式**（`motionGloveSDK_example3_3dView.py`）：新增 `AppMode.CSV_PLAYBACK` 模式，通过顶部 `APP_MODE` 常量切换；CSV 回放使用单定时器架构（`time.monotonic()` 驱动），消除双定时器帧率抖动问题。
- **地平面默认显示**：`build_ground_plane_actor` 返回的地平面 Actor 初始可见性改为 `True`。

### Fixed
- **`pyside6` 版本导致的打包程序退出崩溃**：`setup_python_libs` 原先固定 `pyside6==6.5.3`（其 shiboken6 按 NumPy 1.x 编译），与 `vtk==9.6.0` 组合时程序在退出阶段崩溃（0xC0000005）。现改为 `numpy==2.2.6` + `pyside6==6.11.0`（Windows/Linux 脚本与 README 版本表同步），`[Windows]build.cmd` 从零安装依赖→编译→打包后的可执行文件退出码为 0。
- **`[Windows]build.cmd` 变量被覆盖**：`scripts\[Windows]setup_python_libs.cmd` 会覆盖调用方的 `ROOT_DIR`，导致一条龙脚本第二步找不到编译脚本。现改用 `PROJECT_ROOT`，并给 `setup_python_libs.cmd` 加上 `setlocal` 避免污染调用方环境。
- **`src/csv_to_bvh.py` BVH 骨骼首尾脱节**：手指关节错误使用 6 通道（含位置），导致 Blender 等工具在父骨骼旋转后子骨骼位置错位。修复：手指关节改为 3 通道（仅旋转），骨骼方向完全由 HIERARCHY OFFSET 定义；RightHand / LeftHand 根节点保留 6 通道。
- **`motionGloveSDK_example3_3dView.py` 32 骨数据流虚拟指尖「骨折」**：末梢虚拟骨骼原来沿第三段骨骼的局部 +X 轴延伸，而骨骼静止姿态沿 +Y 轴，导致指尖与手指成 90° 折角。修复：改为沿第三段全局姿态的 +Y 轴延伸（无姿态数据时退化为第三节骨段的实际方向），姿态解算同时抽为 `compute_frame_pose()` 便于单测。用真实 42 骨流自带的末梢位置交叉校验，方向误差 < 0.01°。

### Changed
- **脚本合并为双解释器单文件**：`scripts/` 下原先成对的 `[Windows]xxx.cmd` / `[Linux]xxx.sh` 合并为同一份 `.cmd` 文件
  （首行 `:; exec sh -c "$(sed -n '/^#__SH__/,$p' "$0" | tr -d '\r')" "$0" "$@" #`，cmd 当标签行忽略、sh 取 `#__SH__` 之后的段执行）：
  `setup_python_libs.cmd`、`build_mgsdk_cpp.cmd`、`build_csv_to_bvh.cmd`、`git_pull_latest.cmd`、`open_in_vscode.cmd`；
  `package_for_customer.cmd`、`update_translations.cmd` 补齐 Linux/macOS 段（分别走 `pwsh` 与 `libs/PySide6/lupdate`）。
  根目录 `gen_docs.bat` 移入 `scripts` 并升级为 `scripts/gen_docs.cmd`（doxygen 查找顺序：`DOXYGEN` 环境变量 → Windows 默认路径 → `PATH`）。
  根目录 `[Windows]build.cmd` 与 `scripts/[Linux]build_dist.sh` 合并为根目录 `build.cmd`；根目录重复的
  `[Windows]git_pull_latest.cmd`、`[Windows]open_in_vscode.bat` 删除。所有合并后的文件统一 CRLF、无 BOM，
  后缀统一 `.cmd`；CI（`.github/workflows/ci-3dview.yml`）改为 Windows 用 `call scripts\xxx.cmd`、Linux 用 `sh scripts/xxx.cmd`。
- **`package_for_customer.ps1` 跨平台**：无 `robocopy` 时回退到 PowerShell 递归复制（对齐 `/XD`、`/XF` 语义）；
  7-Zip 探测不再假设 `$env:ProgramFiles` 存在（非 Windows 只看 PATH），缺失时回退 `Compress-Archive`；
  暂存目录改用 `Join-Path` 逐段拼接，避免反斜杠在 Linux 上被当成文件名。
- **一条龙打包脚本更名**：根目录 `[Windows]build_dist.cmd` → `[Windows]build.cmd`（README、CHANGELOG 与脚本内的用法说明同步更新）。
- **客户分发包包含构建入口**：`[Windows]build.cmd` 与 `MotionGlove3DViewer.spec`（以及 `csv_to_bvh.spec`）改为随包发出，客户可直接构建可执行文件；`scripts/[Linux]build_dist.sh` 仍不打包。打包脚本新增校验，暂存目录缺少 `[Windows]build.cmd` / `MotionGlove3DViewer.spec` 时直接报错。
- **仓库目录整理**：`CLAUDE.md` 更名为 `AGENTS.md`；`fonts/`、`csvPlayer/`、`docs/`、`MotionGloveBVH/`、`triad_openvr/`、`CSV_PLAYBACK_UserManual.md/.pdf` 统一移入 `tools/`；示例程序、PyInstaller spec、README 与手册内的相对路径同步更新。
- `src/motionGloveSDK.py`：改为对 `src/native` 的薄门面，函数名与返回值语义保持不变；原生库不可用时抛 `MotionGloveNativeError`（`MotionGloveSDK_ListenUDPPort` 仍以 `-1` 表示失败）。
- `src/glove_frame_assembler.py`、`src/decode_glove_csv.py`：不再参与 UDP 数据流路径，仅保留给 `motionGloveSDK_rawReceiver.py`（原始数据调试）与 CSV 回放使用。
- `MotionGlove3DViewer.spec`：打包时自动收集 `MotionGloveSDK` 原生库（缺失时打包直接失败）；`src/native/loader.py` 增加 PyInstaller 冻结环境的库查找路径。
- `motionGloveSDK_example3_3dView.py`：轮询线程与左侧面板在原生库不可用时不再崩溃，改为提示编译指引。
- `scripts/git_pull_latest.cmd`（cmd / sh 双解释器）：拉取代码后自动同步 submodule 并重新编译原生库。
- **末梢虚拟骨骼移除**：删除固定长度末梢骨骼合成逻辑（`FINGERTIP_BONE_LENGTH`、`_FINGERTIP_BONES`、`_fingertip_actors` 及 `_on_timer` 中的四元数 Y 轴投影代码），改由发送端传入的真实 `*3End` 骨骼位置替代。
- `src/decode_glove_csv.py`：骨骼计数从 `KHHS32_SKELETON_COUNT` 更新为 `KHHS42_SKELETON_COUNT`，支持 42 骨骼帧的解析；欧拉角转四元数改用 `src/xsqeconverter.py`，移除对旧 `euler_to_quat.py` 的依赖。
- `_BONE_LINKS`：从 30 条扩展至 40 条，新增 10 条 `*3 → *3End` 末梢连线；`_BONE_PARENT` 自动由 `_BONE_LINKS` 派生，覆盖全部 42 骨骼。
- `python_draw3d/draw_config_io.py`：骨骼连线默认粗细从 2 调整为 10；`DrawConfigWidget` 连线粗细 Slider 最大值从 20 扩展至 30。
- **世界坐标轴大小**：`add_axes_to_renderer` 调用时 `length` 从 0.05 缩减至 0.025（缩小一半）。
- `src/euler_to_quat.py` 已删除，功能统一由 `src/xsqeconverter.py` 提供。


