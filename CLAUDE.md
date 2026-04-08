# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MotionGloveSDK Python** is a Python SDK for receiving and processing real-time motion capture data from MotionGlove hardware devices. The SDK receives skeletal bone data via UDP, reassembles fragmented packets, and provides clean access to 32-joint hand skeleton data (~60 Hz). A 3D visualization module using VTK is included.

## Environment Setup

Dependencies are installed locally to `libs/` (not system Python) using pip `--target`:

```bash
# Windows
scripts\[Windows]setup_python_libs.cmd

# Linux/macOS
bash scripts/[Linux]setup_python_libs.sh
```

**Python 3.10+ is required.** Runtime deps (vtk, numpy, matplotlib, Pillow, **pyside6**) land in `libs/`; dev tools (pyinstaller, pybind11) go to system Python.

## Running Examples

```bash
# Basic frame reception test
python motionGloveSDK_example1.py

# Real-time palm angle readout
python motionGloveSDK_example2.py

# Full 3D skeletal viewer (requires VTK)
python motionGloveSDK_example3_3dView.py

# Raw UDP debugging
python motionGloveSDK_rawReceiver.py [--print-raw]
```

## CI Smoke Tests

The CI workflow (`.github/workflows/ci-3dview.yml`) runs `motionGloveSDK_example3_3dView.py` on Windows, Ubuntu 22.04, and Ubuntu 24.04 with Python 3.10.

Environment variables that control CI behavior:
- `MOTIONGLOVE_CI=1` — activates CI mode (no blocking input/timer loops)
- `MOTIONGLOVE_CI_RENDER=0` — skip rendering; exits before constructing `QApplication` (used on both Windows and Linux)
- `MOTIONGLOVE_CI_RENDER=1` — enable offscreen rendering (not used in CI; available for local testing)
- `MOTIONGLOVE_CI_SECONDS=0.2` — how long to run the render loop (only relevant when `MOTIONGLOVE_CI_RENDER=1`)

To replicate a CI run locally:
```bash
MOTIONGLOVE_CI=1 MOTIONGLOVE_CI_RENDER=0 python motionGloveSDK_example3_3dView.py
```

## Architecture

### Data Flow

```
UDP Socket (port 5001)
    ↓ raw bytes
GloveFrameAssembler          # reassembles fragmented packets by frame number
    ↓ complete CSV payload
decode_glove_csv()           # parses CSV → GloveFrame + 32 SingleSkeleton objects
    ↓
_actor_store {name: frame}   # thread-safe cache (RLock), keyed by actor/avatar name
    ↓ poll
Application code
```

### Core Modules (`src/`)

| Module | Role |
|--------|------|
| `motionGloveSDK.py` | Public API + background UDP recv thread |
| `definitions.py` | All data structures (`GloveFrame`, `SingleSkeleton`, `StreamHeader`, enums) |
| `glove_frame_assembler.py` | Reassembles split UDP packets with matching frame number (`fn`) |
| `decode_glove_csv.py` | Parses CSV-encoded packet body into typed objects |
| `euler_to_quat.py` | Euler → quaternion conversion supporting all 6 rotation orders |
| `port_occupier.py` | Diagnostic: identifies process holding a UDP port (cross-platform) |

### 3D Visualization (`python_draw3d/`)

VTK-based pipeline embedded in a **PySide6 `QMainWindow`** (`motionGloveSDK_example3_3dView.py`). Key components:

- 32 `BoneJointActor` instances (sphere + RGB axes per joint)
- 30 `BoneLinkActor` instances (lines connecting parent–child bone pairs)
- `vtkAxesActor` at the world origin (toggleable via right-click menu)
- `ground_plane.py` — grey grid on the X–Z plane, 5 cm spacing (toggleable via right-click menu)

Window chrome: menu bar (文件→退出, 帮助→关于 Qt), left info panel (UDP source IP/port, port error if bind fails), status bar.

Mouse controls: rotate (left), zoom (right-drag), pan (middle), spacebar to reset camera. Short right-click opens context menu.

### UI Files (`ui/`)

| File | Role |
|------|------|
| `left_panel.ui` | Qt Designer layout for the left network info panel (fixed width 220 px) |
| `left_panel_widget.py` | `LeftPanelWidget` controller — loads `.ui` at runtime via `QUiLoader`, exposes `lbl_ip`, `lbl_port`, `lbl_error`; provides `show_port_error(lines)` and `clear_error()` |

The `.ui` file can be edited directly with Qt Designer. No compilation step required — `QUiLoader` loads it at runtime. `pyrightconfig.json` includes `ui/` in `extraPaths` so Pyright resolves the import.

### Public SDK API

```python
MotionGloveSDK_ListenUDPPort(port)             # start background recv thread
MotionGloveSDK_isGloveNewFramePending(name)    # check if new frame arrived
MotionGloveSDK_GetGloveSkeletonsFrame(name)    # get latest GloveFrame
MotionGloveSDK_resetGloveNewFramePending(name) # clear pending flag
MotionGloveSDK_CloseUDPPort()                  # stop and clean up
MotionGloveSDK_GetLastRemoteAddr()             # returns (ip, port) of last UDP sender, or None
```

### Skeletal Structure (32 bones)

- Bones 0–15: Right hand — index 0 = `RightHand` (root), then thumb/index/middle/ring/pinky (3 joints each)
- Bones 16–31: Left hand — same layout, root = `LeftHand`

Each `SingleSkeleton` carries `position [x,y,z]` (meters), `quat_wxyz`, and `euler_degree`, with `contains_*` flags indicating which fields are populated by the current stream.

### Threading Model

- **Main thread:** application polling
- **Background daemon thread:** `_recv_loop()` — `socket.recvfrom()` → `GloveFrameAssembler` → callback → `_actor_store`
- `_actor_store` is protected by `threading.RLock()`

## Type Checking

Pyright is configured via `pyrightconfig.json`. It adds `python_draw3d/` and `libs/` to `extraPaths`. Run with:
```bash
pyright
```
