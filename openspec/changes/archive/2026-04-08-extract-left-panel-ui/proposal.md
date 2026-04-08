## Why

The left info panel is currently built entirely in Python code inside `_build_central()`, making visual tweaks (layout, spacing, labels, adding new widgets) require code edits. Extracting it to a Qt Designer `.ui` file lets any team member iterate on the panel's appearance with a visual editor without touching Python, and establishes a `ui/` folder convention for future panels and dialogs.

## What Changes

- Create a `ui/` subfolder at the project root to hold `.ui` files and their companion Python controller classes
- Create `ui/left_panel.ui` — a Qt Designer file representing the left info panel (fixed width, network data source section with IP and port labels)
- Create `ui/left_panel_widget.py` — a thin Python controller that loads `left_panel.ui` via `QUiLoader` and exposes `lbl_ip` and `lbl_port` for the main window to update
- Modify `motionGloveSDK_example3_3dView.py` to instantiate `LeftPanelWidget` from `ui/left_panel_widget.py` instead of building the panel inline in `_build_central()`

## Capabilities

### New Capabilities

- `left-panel-ui-file`: Qt Designer `.ui` file and companion controller for the left info panel; the panel can be visually edited in Qt Designer and loaded at runtime

### Modified Capabilities

- `pyside6-main-window`: The main window now loads the left panel from a `.ui` file instead of constructing it inline — the observable behavior (IP/port labels, fixed width) is unchanged, but the source of truth for the layout moves to `ui/left_panel.ui`
- `network-info-panel`: The panel's widget structure (labels, layout) is now defined in `ui/left_panel.ui`; the `lbl_ip` / `lbl_port` update contract is preserved but now goes through the controller class

## Impact

- New folder: `ui/` at project root
- New files: `ui/left_panel.ui`, `ui/left_panel_widget.py`
- Modified: `motionGloveSDK_example3_3dView.py` — `_build_central()` refactored
- New runtime dependency on `PySide6.QtUiTools.QUiLoader` (already part of `pyside6`, no new package needed)
- Qt Designer (bundled with PySide6 as `pyside6-designer`) can open and edit `ui/left_panel.ui` directly
