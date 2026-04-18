## 1. UI 调整

- [x] 1.1 在 `ui/csv_import_panel.ui` 的 BVH→FBX 分组中，为 Blender 路径区域新增按钮 `bvh2fbx_blender_auto_btn`
- [x] 1.2 将该按钮放在“选择Blender路径”按钮下方，并保证现有控件名称与布局不被破坏
- [x] 1.3 为新按钮设置合适的按钮文本，纳入 Qt 翻译系统

## 2. Widget 逻辑

- [x] 2.1 在 `ui/csv_import_widget.py` 中获取新按钮引用并连接点击信号
- [x] 2.2 实现自动检测槽函数，从 `Path.cwd() / "libs"` 开始查找 Blender 目录
- [x] 2.3 仅扫描 `libs/` 一级子目录，按目录名不区分大小写包含 `blender` 作为候选
- [x] 2.4 对候选目录按名称排序后逐个检查 `<candidate>/blender.exe` 是否存在
- [x] 2.5 找到首个有效路径后，将其写入 `bvh2fbx_blender_edit`，调用 `_save_blender_path()` 保存到 `config.json`，并调用 `_update_convert_btn_state()`
- [x] 2.6 若 `libs/` 不存在、未找到任何可用 `blender.exe`、或检测过程中报错，弹出提示并保留现有路径不变

## 3. 验证

- [ ] 3.1 在当前运行目录下创建或确认存在 `libs/<包含blender字符串的目录>/blender.exe`，点击自动检测按钮后确认路径被自动填充
- [ ] 3.2 重启程序，确认 `bvh2fbx_blender_edit` 能从 `config.json` 恢复刚保存的路径
- [ ] 3.3 在存在 BVH 路径的情况下，确认自动检测成功后“转换为 FBX”按钮变为可用
- [ ] 3.4 删除或改名 `libs/` 下的候选目录后再次点击自动检测，确认界面提示“未找到”且不清空已有路径
