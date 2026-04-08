## 1. Create ui/ folder and Qt Designer file

- [x] 1.1 Create the `ui/` directory at the project root
- [x] 1.2 Write `ui/left_panel.ui` — a valid Qt Designer XML file with top-level `QFrame` (objectName `left_panel`, fixedWidth 220), containing a `QVBoxLayout` with: bold title `QLabel` (text `<b>网络数据源</b>`), an IP row `QHBoxLayout` (static label `来源 IP：` + value `QLabel` objectName `lbl_ip`, text `等待中…`, wordWrap true), a port row `QHBoxLayout` (static label `端口：` + value `QLabel` objectName `lbl_port`, text `—`), and a vertical spacer at the bottom

## 2. Create LeftPanelWidget controller

- [x] 2.1 Create `ui/left_panel_widget.py` with a `LeftPanelWidget(QWidget)` class
- [x] 2.2 In `LeftPanelWidget.__init__`, resolve the `.ui` path as `Path(__file__).parent / "left_panel.ui"`, load it with `QUiLoader`, and re-parent / embed the loaded widget into `self` via a layout
- [x] 2.3 Expose `self.lbl_ip` and `self.lbl_port` by finding child `QLabel` widgets by their objectNames (`"lbl_ip"`, `"lbl_port"`) on the loaded widget
- [x] 2.4 Set `self.setFixedWidth(220)` on `LeftPanelWidget` so the outer widget retains the fixed width regardless of `.ui` settings

## 3. Update motionGloveSDK_example3_3dView.py

- [x] 3.1 Add `ui/` to `sys.path` at the top of the file (alongside the existing `libs/` and `python_draw3d/` insertions)
- [x] 3.2 Import `LeftPanelWidget` from `left_panel_widget` at the top of `_build_qt_app()`
- [x] 3.3 In `_build_central()`, replace the inline `QFrame` + labels construction with `self._left_panel = LeftPanelWidget()` and `h_layout.addWidget(self._left_panel)`
- [x] 3.4 In `_on_timer()`, replace `self._lbl_ip.setText(...)` / `self._lbl_port.setText(...)` with `self._left_panel.lbl_ip.setText(...)` / `self._left_panel.lbl_port.setText(...)`
- [x] 3.5 Remove the now-unused `self._lbl_ip` and `self._lbl_port` direct assignments from `_build_central()`

## 4. Verification

- [x] 4.1 Run CI smoke test: `MOTIONGLOVE_CI=1 MOTIONGLOVE_CI_RENDER=0 python motionGloveSDK_example3_3dView.py` — must pass
- [x] 4.2 Syntax-check `ui/left_panel_widget.py` and `motionGloveSDK_example3_3dView.py` via `ast.parse`
- [x] 4.3 Confirm `ui/left_panel.ui` is well-formed XML (`python -c "import xml.etree.ElementTree as ET; ET.parse('ui/left_panel.ui')"`)
