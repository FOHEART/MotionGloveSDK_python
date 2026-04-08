## Why

The existing 3D viewer is a standalone VTK window with no UI chrome — as the SDK grows, there is no room to add controls, status feedback, or metadata display. Wrapping the viewer in a PySide6 main window now creates the foundation for all future GUI features.

## What Changes

- Introduce PySide6 as a new dependency for the 3D viewer (`motionGloveSDK_example3_3dView.py`)
- Embed the VTK render window inside a PySide6 `QMainWindow` (center widget)
- Add a menu bar: **File → Exit**, **Help → About Qt**
- Add a left-side panel (`QDockWidget` or fixed `QWidget`) showing the live UDP source IP and port
- Add a status bar at the bottom of the main window
- Update `[Windows]setup_python_libs.cmd` and `[Linux]setup_python_libs.sh` to install `pyside6`

## Capabilities

### New Capabilities

- `pyside6-main-window`: PySide6 QMainWindow host that embeds the VTK viewport in the center, provides menu bar, left info panel, and status bar
- `network-info-panel`: Left-side widget that polls and displays the current UDP source IP and port in real time
- `setup-scripts-pyside6`: Updated setup scripts that add PySide6 to the local `libs/` installation

### Modified Capabilities

<!-- None — no existing spec-level behavior changes -->

## Impact

- `motionGloveSDK_example3_3dView.py` — major refactor: VTK initialization moves into a PySide6 embedding layer
- `python_draw3d/` — VTK pipeline largely unchanged; entry point adapts to Qt event loop
- `[Windows]setup_python_libs.cmd`, `[Linux]setup_python_libs.sh` — add `pyside6` to pip install target
- CI workflow may need `pyside6` install and an offscreen Qt platform (`QT_QPA_PLATFORM=offscreen`) on Linux
- New runtime dependency: `pyside6` (≥6.5)
