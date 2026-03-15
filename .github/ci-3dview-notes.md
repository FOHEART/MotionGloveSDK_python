# 3D View CI / CL 记录

本文记录当前 `motionGloveSDK_example3_3dView.py` 为适配 GitHub Actions 与持续集成场景所做的约定，便于后续维护 `CI / CL` 相关内容。

## 涉及文件

- `.github/workflows/ci-3dview.yml`
- `motionGloveSDK_example3_3dView.py`
- `[Windows]setup_python_libs.cmd`
- `[Linux]setup_python_libs.sh`

## 当前 CI 工作流说明

工作流文件：`.github/workflows/ci-3dview.yml`

当前已验证可正常运行的策略如下：

- 触发条件：`push`、`pull_request`
- 运行平台：
  - `windows-latest`
  - `ubuntu-22.04`
  - `ubuntu-24.04`
- Python 版本：`3.10`
- 全局环境变量：
  - `PYTHONUTF8=1`
  - `PYTHONIOENCODING=utf-8`

## 3D Viewer 为 CI 做的兼容处理

`motionGloveSDK_example3_3dView.py` 中已加入以下 CI 兼容逻辑：

### 1. CI 模式识别

通过以下环境变量判断是否进入 CI 模式：

- `MOTIONGLOVE_CI`
- `CI`

满足 `1` / `true` / `yes` 时视为启用。

### 2. 渲染开关控制

通过环境变量 `MOTIONGLOVE_CI_RENDER` 控制是否在 CI 中实际执行渲染：

- `1` / `true` / `yes`：启用渲染
- `0` / `false` / `no`：跳过渲染

若未显式设置：

- Windows 默认跳过渲染
- 非 Windows 默认允许渲染

这样做的原因是：GitHub Hosted Windows Runner 通常不具备稳定可用的 OpenGL 上下文，直接创建渲染窗口容易失败。

### 3. 无渲染模式的冒烟测试

当满足：

- 处于 CI 模式
- 且关闭实际渲染

程序只执行以下轻量检查：

- 验证 `vtk` 可导入
- 创建基础 `vtkSphereSource`
- 连接 `vtkPolyDataMapper`
- 创建 `vtkActor`
- 将 actor 加入 renderer

成功后输出：

- `[CI] VTK pipeline smoke test passed (render skipped).`

此路径不会触发真正的 OpenGL 上下文创建。

### 4. Offscreen 渲染冒烟测试

当 CI 中允许渲染时：

- 启用 `render_window.SetOffScreenRendering(1)`
- 初始化 interactor
- 渲染数帧后退出

渲染停留时间由 `MOTIONGLOVE_CI_SECONDS` 控制，当前默认值为：

- `0.5`

成功后输出：

- `[CI] Offscreen render smoke test passed.`

### 5. 资源清理

无论是跳过渲染还是进行 offscreen 渲染，CI 路径都会在退出前调用：

- `motionGloveSDK.MotionGloveSDK_CloseUDPPort()`

避免端口或 SDK 状态残留。

## 平台差异说明

### Windows

CI 中执行：

- `call "[Windows]setup_python_libs.cmd"`
- `python motionGloveSDK_example3_3dView.py`

当前环境变量：

- `MOTIONGLOVE_CI=1`
- `MOTIONGLOVE_CI_SECONDS=0.2`
- `MOTIONGLOVE_CI_RENDER=0`

说明：

- Windows 仅做 VTK 管线级别冒烟测试
- 不强制创建渲染窗口
- 这样可提升 GitHub Actions 稳定性

### Linux

CI 中执行：

- `bash "[Linux]setup_python_libs.sh"`
- `xvfb-run -a python motionGloveSDK_example3_3dView.py`

当前环境变量：

- `MOTIONGLOVE_CI=1`
- `MOTIONGLOVE_CI_SECONDS=0.2`

说明：

- Linux 通过 `xvfb-run` 提供虚拟显示环境
- 可执行 offscreen 渲染冒烟测试

## 依赖安装约定

### Windows 安装脚本

文件：`[Windows]setup_python_libs.cmd`

当前约定：

1. 将运行时依赖安装到 `libs` 目录
2. 将开发工具安装到系统 Python

运行时依赖当前包含：

- `vtk==9.6.0`
- `numpy==2.2.6`
- `matplotlib==3.10.8`
- `Pillow==12.1.1`
- 以及相关子依赖

开发工具当前包含：

- `pyinstaller==6.19.0`
- `pybind11==2.13.6`

补充说明：

- 脚本顶部执行 `chcp 65001`，用于减少中文输出乱码问题
- 当前版本选择已考虑 Python 3.10 兼容性

## 后续维护建议

后续如果继续调整 `CI / CL` 相关内容，建议保持以下原则：

1. 优先保证 GitHub Actions 冒烟测试稳定通过
2. Windows 与 Linux 的渲染策略分开维护
3. 涉及渲染能力的变更，优先通过环境变量控制，不直接写死
4. 若增加新的 CI 检查项，尽量保持 `motionGloveSDK_example3_3dView.py` 的本地交互行为不受影响
5. 若升级 `vtk`、`numpy` 或 Python 版本，需要同步验证：
   - Windows 安装脚本
   - Linux 安装脚本
   - `.github/workflows/ci-3dview.yml`
   - 3D Viewer 的 CI 分支逻辑

## 建议的后续可选事项

如果后面需要继续补充 `CL` 侧记录，可考虑在本文追加：

- 变更日志摘要
- 每次 CI 调整的原因
- 不同 runner 的兼容性结论
- 常见失败现象与处理方法
