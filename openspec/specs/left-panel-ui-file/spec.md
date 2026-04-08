## ADDED Requirements

### Requirement: Left panel UI file exists and is Qt Designer compatible
A file `ui/left_panel.ui` SHALL exist at the project root's `ui/` subfolder. It SHALL be a valid Qt Designer XML file that can be opened and edited in Qt Designer (`pyside6-designer`). The top-level widget SHALL be a `QFrame` or `QWidget` with a fixed width of 220 px.

#### Scenario: File opens in Qt Designer
- **WHEN** the user opens `ui/left_panel.ui` in Qt Designer
- **THEN** the panel layout is displayed visually with all labels and rows editable

#### Scenario: UI file loads at runtime
- **WHEN** the application starts and `QUiLoader` loads `ui/left_panel.ui`
- **THEN** no exception is raised and a valid `QWidget` is returned

### Requirement: LeftPanelWidget controller class
A file `ui/left_panel_widget.py` SHALL exist and define a class `LeftPanelWidget(QWidget)` that loads `ui/left_panel.ui` via `QUiLoader` and exposes `lbl_ip` and `lbl_port` as accessible attributes (instances of `QLabel`).

#### Scenario: Controller exposes label attributes
- **WHEN** `LeftPanelWidget()` is instantiated
- **THEN** `widget.lbl_ip` and `widget.lbl_port` are non-None `QLabel` instances whose `setText()` can be called

#### Scenario: UI file path is resolved relative to the module
- **WHEN** `LeftPanelWidget` is imported and instantiated from any working directory
- **THEN** the `.ui` file is found correctly without depending on `os.getcwd()`
