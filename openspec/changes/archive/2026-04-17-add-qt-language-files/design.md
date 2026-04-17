# Design: Qt 本地化加载与语言切换

## 概览
使用 Qt 的 `QTranslator` 加载编译后的 `.qm` 翻译文件（存放在 `translations/`）。在应用启动阶段读取 `config.json` 中的 `language` 字段并加载对应翻译；若无配置则使用系统或默认（`en`）。

## 文件与位置
- 语言资源：`translations/zh_CN.qm`（中文），`translations/en.qm`（英文/通常为空或占位）。
- 配置文件：项目根目录 `config.json`，结构示例：
  {
    "language": "zh_CN"
  }
- 代码改动：`motionGloveSDK_example3_3dView.py`：
  - 在 `_build_qt_app()` 中，创建并注册 `QTranslator`；将 Translator 存为窗口实例属性以便在运行时管理。
  - 在 `_build_menu()` 中添加“设置”→“语言”菜单，并为“中文”和“English”创建 `QAction`（可 checkable，互斥）。
  - 语言选择回调：如果选择值与当前 `config.json` 不同，保存新值到 `config.json`，并弹出 `QMessageBox` 提示“需重启应用以应用语言更改”，按钮为“立即重启/稍后”。
  - 立即重启实现：调用 `QApplication.quit()` 后使用外部脚本或平台启动器重新启动（实现建议：在主入口 `main()` 检测命令行参数 `--restart`，或在 Windows 上用 `subprocess.Popen([sys.executable]+sys.argv)` 在退出前启动新进程）。为了最简实现，本次变更将提示用户手动重启并提供“立即重启”选项，该选项会尝试自动重启当前进程。

## 启动流程
1. 程序启动时：
   - 读取 `config.json`（如果不存在则使用 `{}`）。
   - 从 `language` 字段确定要加载的语言标识（如 `zh_CN` 或 `en`）。
   - 创建 `QTranslator()` 并 `load()` 对应 `translations/<lang>.qm`。
   - 用 `app.installTranslator(translator)` 应用翻译。
2. 在 UI 创建后（菜单/文字已经使用 `tr()` 或直接字符串），文本将自动根据加载的翻译显示。若某些字符串是硬编码而非通过 Qt 翻译机制，则需改为 `self.tr('文本')` 或 `QCoreApplication.translate()`。

## 运行时切换流程
- 用户在“设置→语言”选择不同语言：
  - 将新语言写入 `config.json`。
  - 弹窗提示需要重启。若用户确认“立即重启”，尝试自动重启：
    - 在 Windows 上使用 `subprocess.Popen([sys.executable] + sys.argv)` 启动新实例，然后 `QApplication.quit()` 退出当前进程。
    - 在其他平台同理。

## 兼容性与回退
- 若 `translations/<lang>.qm` 不存在，记录并回退到默认语言，并在状态栏或日志中提示。
- `config.json` 非法或损坏时以默认语言启动并覆盖回写合法的 `config.json`（需备份旧文件）。

## 国际化文本处理建议
- 尽量使用 Qt 翻译系统：对需要翻译的界面字符串调用 `self.tr("文本")` 或在模块级使用 `QCoreApplication.translate("Context","Text")`。
- 为现有字符串创建 `.ts` 文件，然后用 `lupdate`/`pyside6-lupdate` 提取，使用 Qt Linguist 翻译，最后 `lrelease` 生成 `.qm` 文件。

## 安全与 UX
- 保存语言偏好时保证原子写入（tmp -> rename），避免并发写入损坏 `config.json`。
- 提示重启的对话框要有明确选择且防止重复弹窗。
