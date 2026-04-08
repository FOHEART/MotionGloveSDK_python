## ADDED Requirements

### Requirement: UDP source address exposed by SDK
`motionGloveSDK` SHALL expose a function `MotionGloveSDK_GetLastRemoteAddr()` that returns the `(ip: str, port: int)` tuple of the most recently received UDP packet sender, or `None` if no packet has been received yet.

#### Scenario: Remote address available after first packet
- **WHEN** at least one UDP packet has been received from a remote sender
- **THEN** `MotionGloveSDK_GetLastRemoteAddr()` returns `(ip_string, port_int)`

#### Scenario: No packets received yet
- **WHEN** the UDP port is bound but no packet has arrived
- **THEN** `MotionGloveSDK_GetLastRemoteAddr()` returns `None`

### Requirement: Left-side network info panel
The application SHALL display a fixed-width panel on the left side of the main window. The panel SHALL show the UDP source IP address and port number, updated on each timer tick (~60 Hz). The panel's widget structure SHALL be defined in `ui/left_panel.ui` and loaded at runtime by `LeftPanelWidget`; the observable behavior (IP/port display, fixed width ≤240 px, waiting placeholder) SHALL be identical to the inline-built panel.

#### Scenario: Panel shows IP and port when data is flowing
- **WHEN** UDP packets are arriving from a sender
- **THEN** the left panel displays the sender's IP address and port number

#### Scenario: Panel shows waiting state before first packet
- **WHEN** no UDP packet has been received yet
- **THEN** the left panel displays a "Waiting..." or equivalent placeholder

#### Scenario: Panel layout is fixed-width and non-obstructive
- **WHEN** the application window is at its default size (1366×768)
- **THEN** the left panel occupies a fixed width (≤240 px) and the VTK viewport fills the remaining space
