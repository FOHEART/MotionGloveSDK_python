## ADDED Requirements

### Requirement: Start/Stop UDP receive controls in left panel
The left panel SHALL contain a "开始" (Start) button and a "停止" (Stop) button that control the UDP data receive loop. At application startup, receiving SHALL be active: the Start button SHALL be disabled and the Stop button SHALL be enabled. When the Stop button is clicked, the application SHALL call `MotionGloveSDK_CloseUDPPort()` and update button states (Stop disabled, Start enabled). When the Start button is clicked, the application SHALL call `MotionGloveSDK_ListenUDPPort(port)` and update button states (Start disabled, Stop enabled). If the port bind fails on Start, the error SHALL be shown in `lbl_error` and the Start button SHALL remain enabled.

#### Scenario: Default state on launch with successful bind
- **WHEN** the application starts and `MotionGloveSDK_ListenUDPPort` returns 0
- **THEN** the Start button is disabled and the Stop button is enabled

#### Scenario: Default state on launch with failed bind
- **WHEN** the application starts and `MotionGloveSDK_ListenUDPPort` returns -1
- **THEN** the Start button is enabled and the Stop button is disabled, and `lbl_error` shows the occupier info

#### Scenario: Stop receiving
- **WHEN** the user clicks the Stop button
- **THEN** `MotionGloveSDK_CloseUDPPort()` is called, the Stop button becomes disabled, the Start button becomes enabled, and the IP/port labels are reset to their placeholder values

#### Scenario: Restart receiving successfully
- **WHEN** the user clicks the Start button and `MotionGloveSDK_ListenUDPPort` returns 0
- **THEN** the Start button becomes disabled, the Stop button becomes enabled, and `lbl_error` is cleared

#### Scenario: Restart receiving with port still occupied
- **WHEN** the user clicks the Start button and `MotionGloveSDK_ListenUDPPort` returns -1
- **THEN** the Start button remains enabled, the Stop button remains disabled, and `lbl_error` shows updated occupier info
