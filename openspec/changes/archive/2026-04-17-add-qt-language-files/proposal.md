# Proposal: 添加 Qt 语言文件并在菜单中添加语言选择

## What (做什么)
在应用中添加 Qt 本地化支持：
- 新增翻译文件（例如 `translations/zh_CN.qm` 和 `translations/en.qm`）。
- 在主菜单栏添加一项“设置”，其下增加子菜单“语言”，包含“中文”和“English”。
- 将当前语言设置保存到项目根目录的 `config.json`。
- 应用启动时读取 `config.json` 并加载对应语言。
- 当用户选择与当前语言不一致的语言时，提示重启；重启后生效。

## Why (为什么)
方便不同语言用户使用界面，并保持设置持久化，提升本地化体验。

## Scope
- 仅改动 Qt 界面层（PySide6 部分）和增加语言资源文件与配置读写。
- 不翻译业务数据或 CSV 内容，仅界面文本。

## Deliverables
- `openspec/changes/add-qt-language-files/` 下的提案、设计、任务文档（本变更）。
- `translations/` 目录中的 `.ts/.qm` 或已编译的 `.qm` 文件（说明如何生成）。
- 代码修改点（在 `motionGloveSDK_example3_3dView.py` 中添加菜单、读取/保存 `config.json`、加载 `QTranslator`）。
