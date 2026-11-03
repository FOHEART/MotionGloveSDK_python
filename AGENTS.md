# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MotionGloveSDK Python** is a Python SDK for receiving real-time motion capture data from MotionGlove hardware devices. The UDP receive path, packet reassembly and CSV parsing are performed **entirely by the C++ SDK** vendored as a git submodule at `third_party/MotionGloveSDK_cpp`; Python reaches it through the `src/native` adapter layer (ctypes) and exposes clean access to 32/42-joint hand skeleton data (~60 Hz). A 3D visualization module using VTK is included.

## Environment Setup

Dependencies are installed locally to `libs/` (not system Python) using pip `--target`:

All `scripts/*.cmd` files are **dual-interpreter** (same file runs under Windows `cmd.exe`
and POSIX `sh`); they must stay CRLF and BOM-free.

```bash
# Windows
scripts\setup_python_libs.cmd

# Linux/macOS
sh scripts/setup_python_libs.cmd
```

**Python 3.10+ is required.** Runtime deps (vtk, numpy, matplotlib, Pillow, **pyside6**) land in `libs/`; dev tools (pyinstaller, pybind11) go to system Python.

The native library is also required at runtime:

```bash
git submodule update --init --recursive

# Windows (Visual Studio 2022+ and CMake required)
scripts\build_mgsdk_cpp.cmd

# Linux/macOS (g++ and CMake required)
sh scripts/build_mgsdk_cpp.cmd
```

Outputs go to `build/mgsdk_cpp/install/` (`bin/MotionGloveSDK.dll` on Windows, `lib/libMotionGloveSDK.so` elsewhere).
`src/native/loader.py` auto-discovers it; set `MOTIONGLOVE_NATIVE_LIB` to point at a specific file or directory.

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

The CI workflow (`.github/workflows/ci-3dview.yml`) has two jobs:

1. **`smoke-test`** — runs `motionGloveSDK_example3_3dView.py` on Windows, Ubuntu 22.04, and Ubuntu 24.04 with Python 3.10. It does **not** check out the submodule or build the native library, so it only exercises the GUI/VTK import path.
2. **`native-backend`** — checks out submodules recursively, builds `third_party/MotionGloveSDK_cpp`, then runs `scripts/verify_native_abi.py` and `scripts/native_smoke_test.py` on Windows and Ubuntu 24.04.

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
    ↓ raw datagrams
MotionGloveSDK.dll / libMotionGloveSDK.so   # third_party/MotionGloveSDK_cpp (C++)
    │   • background recv thread
    │   • GloveSplitFrameMgr — reassembles fragments by frame number (`fn`, `subpackage a/b`)
    │   • CSV parsing → pos / euler / quat per skeleton, euler→quat conversion
    │   • per-actor cache: KHHS32PosAttitude / KHHS42PosAttitude + isNewFramePending
    ↓ ctypes calls (src/native)
NativeBackend.is_pending / get_frame      # src/native/backend.py
    ↓ struct → dataclass conversion
mapper.to_glove_frame()                   # src/native/mapper.py
    ↓
GloveFrame (src/definitions.py)
    ↓ poll
Application code
```

### Core Modules (`src/`)

| Module | Role |
|--------|------|
| `motionGloveSDK.py` | Public API facade; thin delegation to `src/native` (keeps C++ function names) |
| `definitions.py` | All data structures (`GloveFrame`, `SingleSkeleton`, `StreamHeader`, enums) |
| `native/abi.py` | **ctypes mirror of the C++ structs/enums** — the only file coupled to C++ memory layout |
| `native/loader.py` | Locates/loads the native library and binds export prototypes |
| `native/mapper.py` | Native struct → `GloveFrame` conversion (derives `contains_*` from the header) |
| `native/backend.py` | `NativeBackend` — stable Python semantics over the volatile C++ ABI |
| `native/errors.py` | `MotionGloveNativeError` / `NativeLibraryNotFound` |
| `glove_frame_assembler.py` | Legacy Python packet reassembly — now only used by `motionGloveSDK_rawReceiver.py` |
| `decode_glove_csv.py` | Legacy Python CSV parser — now only used by CSV playback and `rawReceiver` |
| `csv_frame_reader.py` | `CsvFrameReader` — preloads a MotionGlove CSV export, serves frames via `next_frame()` |
| `xsqeconverter.py` | Euler ↔ quaternion conversion (Python port of Movella's xsqeconverter.cpp); all 6 rotation orders |
| `port_occupier.py` | Diagnostic: identifies process holding a UDP port (cross-platform) |

### Adapter layer boundary (`src/native/`)

The C++ project changes often, so everything ABI-related is quarantined in `src/native`:

| C++ change | File to update |
|---|---|
| Struct field/order/alignment | `native/abi.py` (verify with `scripts/verify_native_abi.py`) |
| Exported function signature / return code | `native/loader.py` `_bind()`, sometimes `native/backend.py` |
| New skeleton layout | `native/abi.py` `FRAME_STRUCT_BY_FORMAT` + `native/mapper.py` |

`scripts/abi_probe.cpp` prints the real `sizeof`/`offsetof` from the C++ headers; `scripts/verify_native_abi.py` compiles it and diffs it against `native/abi.py`.

Notes on C++ semantics the adapter compensates for:
- `SingleSkeletonDef` has **no** `contains_*` flags — `mapper.py` derives them from `hdr.skeletonPosition` / `hdr.skeletonAttitude`.
- `remotePort` is stored as `sockaddr_in.sin_port` (network byte order) — `mapper.decode_remote_port()` applies `ntohs`.
- 32-segment frames are returned natively as 32 entries; `mapper.py` maps them to 42-index `bone_index` via `BONE_INDEX_MAP_32_TO_42`.
- The C++ SDK exposes no actor enumeration; `MotionGloveSDK_GetActorNames()` therefore returns names observed via `is_pending`/`get_frame`.

### 3D Visualization (`python_draw3d/`)

VTK-based pipeline embedded in a **PySide6 `QMainWindow`** (`motionGloveSDK_example3_3dView.py`). Key components:

- 32 `BoneJointActor` instances (sphere + RGB axes per joint)
- 30 `BoneLinkActor` instances (lines connecting parent–child bone pairs)
- `vtkAxesActor` at the world origin (toggleable via right-click menu)
- `ground_plane.py` — grey grid on the X–Z plane, 5 cm spacing (toggleable via right-click menu)
- `draw_config_io.py` — `DrawConfig` dataclass + JSON `save_config`/`load_config` for joint/link/axis visual properties

Window chrome: menu bar (文件→退出, 帮助→关于 Qt), left info panel (UDP source IP/port, port error if bind fails), status bar.

Mouse controls: rotate (left), zoom (right-drag), pan (middle), spacebar to reset camera. Short right-click opens context menu.

### AppMode — dual startup mode

`motionGloveSDK_example3_3dView.py` supports two modes switched by a single top-level constant:

```python
APP_MODE = AppMode.UDP_STREAM   # real-time UDP (default)
APP_MODE = AppMode.CSV_PLAYBACK # replay a saved CSV file
```

- **`UDP_STREAM`**: left panel = `LeftPanelWidget`; background `_poll` thread feeds `_latest_frame[0]`
- **`CSV_PLAYBACK`**: left panel = `CsvImportWidget`; `QTimer` ticks at the selected fps, calling `CsvFrameReader.next_frame()` to write `_latest_frame[0]`
- Both modes share the same `_on_timer` VTK render loop and right-side `DrawConfigWidget`

The render timer (`_on_timer`) always reads `_latest_frame[0]` regardless of mode.

### UI Files (`ui/`)

| File | Role |
|------|------|
| `left_panel.ui` | Qt Designer layout for the left network info panel (fixed width 220 px) |
| `left_panel_widget.py` | `LeftPanelWidget` — loads `.ui` via `QUiLoader`; exposes `lbl_ip`, `lbl_port`, `lbl_error`, `show_port_error()`, `clear_error()` |
| `draw_config_widget.py` | `DrawConfigWidget` (220 px) — sliders + color pickers for joint radius/color, link width/color, axis length; calls `draw_config_io.py` |
| `csv_import_widget.py` | `CsvImportWidget` (220 px) — file picker, fps combo (10/24/30/60 Hz), play/pause/reset buttons, progress slider; all interaction via PySide6 signals |

The `.ui` file can be edited directly with Qt Designer. No compilation step required — `QUiLoader` loads it at runtime. `pyrightconfig.json` includes `ui/` in `extraPaths` so Pyright resolves the import.

### Public SDK API

```python
MotionGloveSDK_ListenUDPPort(port)             # start C++ recv thread (returns 0 / -1)
MotionGloveSDK_isGloveNewFramePending(name)    # check if new frame arrived
MotionGloveSDK_GetSkeletonsFrameType(name)     # 32 / 42 / OpenXR, or None
MotionGloveSDK_GetGloveSkeletonsFrame(name)    # get latest GloveFrame (auto 32/42 dispatch)
MotionGloveSDK_resetGloveNewFramePending(name) # clear pending flag
MotionGloveSDK_CloseUDPPort()                  # stop and clean up
MotionGloveSDK_GetLastRemoteAddr()             # (ip, port) of last fetched frame, or None
MotionGloveSDK_GetActorNames()                 # stream names observed so far
MotionGloveSDK_IsAvailable()                   # native library loadable?
MotionGloveSDK_GetBackendName()                # always "native"
MotionGloveSDK_GetNativeLibraryPath()          # loaded library path
```

`MotionGloveSDK_ListenUDPPort` reports failures as `-1`; every other function raises
`MotionGloveNativeError` when the native library cannot be loaded.

### Skeletal Structure (32 / 42 bones)

- **42-segment stream** (default for current firmware): `frame.skeletons` has 42 entries, `bone_index` 0–41, names from `definitions.BONE_NAMES`.
- **32-segment stream**: `frame.skeletons` has 32 entries; `bone_index` is mapped to the 42-segment index via `BONE_INDEX_MAP_32_TO_42` (the 3D viewer relies on `len(frame.skeletons) == 32` to synthesise virtual fingertip nodes).

Each `SingleSkeleton` carries `position [x,y,z]` (meters), `quat_wxyz`, and `euler_degree`, with `contains_*` flags indicating which fields are populated by the current stream.

### Threading Model

- **Main thread:** application polling (`_on_timer` render loop, `_poll` thread in the viewer)
- **Background C++ thread:** `recvfrom()` → `GloveSplitFrameMgr` → per-actor cache, all inside the native library
- The C++ side guards its actor cache with a read/write lock; ctypes releases the GIL for each call, so Python never needs its own frame lock (the viewer only locks `_latest_frame`)

## Type Checking

Pyright is configured via `pyrightconfig.json`. It adds `python_draw3d/` and `libs/` to `extraPaths`. Run with:
```bash
pyright
```
