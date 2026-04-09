## MODIFIED Requirements

### Requirement: Left-side network info panel
The application SHALL display a fixed-width panel on the left side of the main window. The panel SHALL show the UDP source IP address and port number, updated on each timer tick (~60 Hz). The panel's widget structure SHALL be defined in `ui/left_panel.ui` and loaded at runtime by `LeftPanelWidget`; the observable behavior (IP/port display, fixed width ≤240 px, waiting placeholder) SHALL be identical to the inline-built panel. The panel SHALL additionally contain a "开始" (Start) button and a "停止" (Stop) button positioned below the IP/port info area, controlling the UDP receive loop. When receiving is stopped, the IP address and port labels SHALL reset to their placeholder values.

#### Scenario: Panel shows IP and port when data is flowing
- **WHEN** UDP packets are arriving from a sender
- **THEN** the left panel displays the sender's IP address and port number

#### Scenario: Panel shows waiting state before first packet
- **WHEN** no UDP packet has been received yet
- **THEN** the left panel displays a "Waiting..." or equivalent placeholder

#### Scenario: Panel layout is fixed-width and non-obstructive
- **WHEN** the application window is at its default size (1366×768)
- **THEN** the left panel occupies a fixed width (≤240 px) and the VTK viewport fills the remaining space

#### Scenario: Panel shows Start/Stop buttons
- **WHEN** the application window is open
- **THEN** the left panel shows both a Start button and a Stop button below the network info labels
