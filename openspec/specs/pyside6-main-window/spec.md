## ADDED Requirements

### Requirement: VTK viewport embedded in QMainWindow
The application SHALL launch a `QMainWindow` with the VTK 3D render viewport occupying the central widget area. Mouse interaction (rotate, zoom, pan) and keyboard shortcuts (spacebar camera reset) SHALL continue to function identically to the standalone VTK window. The left info panel SHALL be loaded from `ui/left_panel.ui` via `LeftPanelWidget` rather than constructed inline.

#### Scenario: Application starts normally
- **WHEN** the user runs `python motionGloveSDK_example3_3dView.py` without CI environment variables
- **THEN** a PySide6 QMainWindow opens with the VTK 3D view in the center, a menu bar at the top, a left info panel (loaded from `ui/left_panel.ui`), and a status bar at the bottom

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

### Requirement: 主窗口支持多启动模式
主窗口 SHALL 根据 `APP_MODE` 枚举值在启动时选择不同的左侧面板和数据驱动逻辑：`UDP_STREAM` 模式行为与现有规格完全一致；`CSV_PLAYBACK` 模式加载 `CsvImportWidget`、不启动 UDP 后台线程、改用 CSV 播放定时器驱动 `_latest_frame[0]`。

#### Scenario: UDP_STREAM 模式启动
- **WHEN** `APP_MODE == AppMode.UDP_STREAM`
- **THEN** 主窗口左侧加载 `LeftPanelWidget`，`_start_sdk_poll()` 被调用，`_start_render_timer()` 正常运行，行为与修改前完全一致

#### Scenario: CSV_PLAYBACK 模式启动
- **WHEN** `APP_MODE == AppMode.CSV_PLAYBACK`
- **THEN** 主窗口左侧加载 `CsvImportWidget`，`_start_sdk_poll()` 不被调用，主窗口持有 `CsvFrameReader` 引用，`_csv_timer` 在用户点击播放后启动

#### Scenario: 两种模式共用渲染逻辑
- **WHEN** `_latest_frame[0]` 被任何来源（UDP 轮询 或 CSV 定时器）更新
- **THEN** 16ms 渲染定时器 `_on_timer` 无差别地读取并渲染到 VTK 场景

## ADDED Requirements

### Requirement: End-node bones rendered as position-only joint spheres
The application SHALL render each of the 10 end-node bones (`*3End`) as a joint sphere at the bone's real world-space position. End-node joint actors SHALL use `set_position_only()` and SHALL NOT display local coordinate axis tripods. The 10 end-node bones SHALL be connected to their respective `*3` parent bones by `BoneLinkActor` lines, rendered identically to all other bone links.

#### Scenario: Fingertip sphere appears at real position
- **WHEN** a 42-bone frame is rendered
- **THEN** a joint sphere is visible at each `*3End` bone position, coinciding with the actual fingertip location

#### Scenario: No coordinate axes on end-node joints
- **WHEN** a 42-bone frame is rendered
- **THEN** no RGB axis tripod lines are drawn at any `*3End` joint sphere

#### Scenario: End-node bone link connects parent to fingertip
- **WHEN** a 42-bone frame is rendered
- **THEN** a bone link line connects `RightHandIndex3` to `RightHandIndex3End` (and equivalently for all other finger chains)

## REMOVED Requirements

### Requirement: Fixed-length virtual fingertip bones
**Reason**: Replaced by real end-node position data from the 42-bone skeleton. The fixed-length synthesis was an approximation no longer needed.
**Migration**: The 10 `BoneLinkActor` instances in `_fingertip_actors`, the `FINGERTIP_BONE_LENGTH` constant, and the quaternion Y-axis projection code in `_on_timer` SHALL be removed. The `_FINGERTIP_BONES` list SHALL be removed. End-node bone links are added to `_BONE_LINKS` instead.
