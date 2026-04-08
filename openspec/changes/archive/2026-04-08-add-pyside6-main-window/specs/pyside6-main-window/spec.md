## ADDED Requirements

### Requirement: VTK viewport embedded in QMainWindow
The application SHALL launch a `QMainWindow` with the VTK 3D render viewport occupying the central widget area. Mouse interaction (rotate, zoom, pan) and keyboard shortcuts (spacebar camera reset) SHALL continue to function identically to the standalone VTK window.

#### Scenario: Application starts normally
- **WHEN** the user runs `python motionGloveSDK_example3_3dView.py` without CI environment variables
- **THEN** a PySide6 QMainWindow opens with the VTK 3D view in the center, a menu bar at the top, a left info panel, and a status bar at the bottom

#### Scenario: Mouse interaction works in embedded viewport
- **WHEN** the user drags the mouse in the VTK viewport area
- **THEN** the 3D scene rotates (left button), zooms (right button), or pans (middle button) as before

#### Scenario: Spacebar resets camera
- **WHEN** the user presses spacebar while the VTK viewport has focus
- **THEN** the camera resets to the default position

### Requirement: Menu bar — File menu
The application SHALL provide a **File** menu in the menu bar containing a single action **Exit** that terminates the application cleanly.

#### Scenario: Exit via menu
- **WHEN** the user clicks File → Exit
- **THEN** the application closes, the UDP socket is released, and the process exits with code 0

### Requirement: Menu bar — Help menu with About Qt
The application SHALL provide a **Help** menu in the menu bar containing a single action **About Qt** that displays the standard Qt "About Qt" dialog.

#### Scenario: About Qt dialog shown
- **WHEN** the user clicks Help → About Qt
- **THEN** the standard PySide6 QMessageBox.aboutQt dialog appears showing Qt version and copyright information

### Requirement: Status bar
The application SHALL display a `QStatusBar` at the bottom of the main window. On startup it SHALL show a ready message. It MAY be used by future features for transient messages.

#### Scenario: Status bar visible on launch
- **WHEN** the application window opens
- **THEN** a status bar is visible at the bottom of the window with an initial message (e.g., "Ready")

### Requirement: CI headless mode compatibility
In CI mode (`MOTIONGLOVE_CI=1`), the application SHALL set `QT_QPA_PLATFORM=offscreen` automatically if no display is detected (Linux) or if `MOTIONGLOVE_CI_RENDER=0`. The `MOTIONGLOVE_CI_RENDER=0` fast path (pipeline-only smoke test) SHALL NOT construct a `QApplication`.

#### Scenario: CI render-disabled path exits without QApplication
- **WHEN** `MOTIONGLOVE_CI=1` and `MOTIONGLOVE_CI_RENDER=0`
- **THEN** the VTK pipeline smoke test runs and exits without constructing a QApplication or any Qt widget

#### Scenario: CI offscreen render path uses offscreen Qt platform
- **WHEN** `MOTIONGLOVE_CI=1` and `MOTIONGLOVE_CI_RENDER=1`
- **THEN** `QT_QPA_PLATFORM=offscreen` is active and the application renders one frame and exits cleanly
