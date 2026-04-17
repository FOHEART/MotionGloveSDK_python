# Tasks: Implement Add Qt Language Files & Menu

1. 创建 `translations/` 目录并添加占位翻译文件
   - `translations/zh_CN.ts`（或直接提供已编译的 `zh_CN.qm`）。
   - `translations/en.ts`（或 `en.qm`，英文通常可为空）。
   - 命令参考：
     - 提取：`pyside6-lupdate . -ts translations/zh_CN.ts`
     - 编辑：用 Qt Linguist 翻译 `zh_CN.ts`
     - 编译：`pyside6-lrelease translations/zh_CN.ts` → `translations/zh_CN.qm`

2. 在项目根创建/更新 `config.json` 操作函数
   - 新文件（建议）：`src/config_io.py`，提供 `read_config()` 和 `write_config()`，保证原子写入并返回默认配置 `{}` 当文件不存在或解析失败。

3. 修改 UI 初始化以加载翻译
   - 在 `_build_qt_app()` 开头或 `MotionGloveMainWindow.__init__` 前读取 `config.json`。
   - 根据 `language` 字段加载 `QTranslator`，并 `app.installTranslator(translator)`。
   - 把 `translator` 和当前 `language` 存为 `window` 属性以便后续访问。

4. 在 `MotionGloveMainWindow._build_menu()` 中添加“设置→语言”菜单
   - 新增 `settings_menu = menu_bar.addMenu("设置(&S)")`。
   - 在 `settings_menu` 下添加子菜单 `language_menu = settings_menu.addMenu("语言")`。
   - 添加可选项 `act_zh = QAction("中文", self, checkable=True)` 与 `act_en = QAction("English", self, checkable=True)`，设为互斥（使用 `QActionGroup`）。
   - 根据当前语言设定 initial checked 状态。
   - 连接信号到 `_on_language_selected(lang_code)` 回调。

5. 实现 `_on_language_selected(lang_code: str)` 回调
   - 若 `lang_code == current_lang`：不做任何事。
   - 否则：调用 `write_config({'language': lang_code})` 保存。
   - 弹出 `QMessageBox` 提示“已更改语言，需要重启以生效。立即重启？”（选项：立即/稍后）。
   - 如用户选择“立即重启”，尝试自动重启：
     - 调用 `subprocess.Popen([sys.executable] + sys.argv)`，随后 `QApplication.quit()`。
     - 若重启失败，显示错误并提示手动重启。

6. 文本准备与翻译
   - 确认界面中所有用户可见字符串均使用 Qt 翻译系统（`tr()` 或 `QCoreApplication.translate`）。
   - 若有硬编码字符串，尽量替换为可翻译形式。

7. 测试
   - 启动应用：无 `config.json` → 应使用默认语言（如英文）。
   - 通过菜单选择中文：保存 `config.json`，弹窗提示重启。
   - 选择立即重启：新进程应加载 `zh_CN.qm` 并显示中文界面。
   - 若 `translations/zh_CN.qm` 缺失，应回退并在日志/状态栏提示。

8. 文档/README 更新
   - 在 `README.md` 或 `CLAUDE.md` 中加说明：如何提取 `.ts`、翻译、编译 `.qm`，以及 `config.json` 的位置与格式。

9. 提交变更并更新 openspec 状态
   - 将上述文件和翻译资源提交到版本控制。


Estimated effort: 2–4 小时（取决于翻译生成与重启实现细节）。
