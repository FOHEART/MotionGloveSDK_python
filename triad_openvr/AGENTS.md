# Triad OpenVR - AI Agent Guide

## Project Overview

**triad_openvr** is a Python wrapper for the [pyopenvr library](https://github.com/cmbruns/pyopenvr) that provides easy-to-use functions for interacting with SteamVR tracked devices (HMDs, controllers, trackers, tracking references).

See [README.md](README.md) for getting started and configuration examples.

## Architecture

### Core Classes

- **`triad_openvr`**: Main class for VR system management
  - Initializes OpenVR and discovers connected devices
  - Maintains device registry (`self.devices` dict, keyed by device name)
  - Supports optional `config.json` for persistent device naming by serial
  - Handles device activation/deactivation events via `poll_vr_events()`

- **`vr_tracked_device`**: Represents a single tracked device
  - Methods: `get_pose_euler()`, `get_pose_quaternion()`, `get_pose_matrix()`, `sample()`
  - Supports velocity and angular velocity queries
  - Controller-specific: `controller_state_to_dict()` for button/trigger state

- **`pose_sample_buffer`**: Data structure for collecting pose samples over time
  - Stores position (x, y, z) and rotation (Euler/quaternion) data with timestamps
  - Used by the `sample()` method to collect high-frequency tracking data

### Coordinate System & Transformations

- **Coordinate Space**: `TrackingUniverseStanding` (standing play area origin at floor level)
- **Pose Matrix**: 3x4 matrix format from OpenVR
  - Conversion functions: `convert_to_euler()` and `convert_to_quaternion()`
  - Euler angles: yaw, pitch, roll (in degrees)
  - Quaternion: r_w, r_x, r_y, r_z (rotation as quaternion)

## Key Conventions

### Device Naming

- Device names are **persistent** when using `config.json` (maps by device serial)
- Auto-generated names follow pattern: `{type}_{number}` (e.g., `controller_1`, `tracker_0`)
- Access devices via: `v.devices["device_name"]`

### Configuration

- **File**: `config.json` - Maps device serials to human-readable names
- **Format**: Array of device objects with `name`, `type`, `serial`
- **Device Types**: `"HMD"`, `"Controller"`, `"Tracker"`, `"Tracking Reference"`

### Sampling & Polling

- **Real-time polling**: Use `get_pose_euler()` or `get_pose_quaternion()` for single poses
- **High-frequency sampling**: Use `device.sample(num_samples, sample_rate_hz)` for time-series data
- **Event handling**: Call `v.poll_vr_events()` periodically to detect device connect/disconnect

### Common Patterns

```python
# Initialize with optional config file
v = triad_openvr.triad_openvr(configfile_path="config.json")

# Query current pose
pose = v.devices["tracker_1"].get_pose_euler()  # [x, y, z, yaw, pitch, roll]

# Collect high-frequency samples
data = v.devices["controller_1"].sample(1000, 250)  # 1000 samples at 250 Hz
plot(data.time, data.x)

# Stream over network (see udp_emitter.py)
quaternion = v.devices["tracker_1"].get_pose_quaternion()
```

## Test Files & Utilities

- **`tracker_test.py`**: Continuous tracker pose monitoring
- **`controller_test.py`**: Similar to tracker_test but for controllers
- **`udp_emitter.py`**: Streams tracker quaternion data over UDP
- **`udp_receiver.cs`**: C# receiver for UDP-streamed pose data

## Dependencies

- **pyopenvr**: Low-level Python bindings for OpenVR
- **openvr**: C++ OpenVR SDK (required at system level for SteamVR)
- Standard library: `time`, `sys`, `math`, `json`, `struct`, `socket`

## Development Notes

- **Platform**: Linux (see workspace setup)
- **Python Version**: Target Python 3.6+ (uses f-strings and modern features)
- **LRU Cache**: Used on `get_serial()` for performance
- **Event-Driven**: Device discovery can be event-driven via `poll_vr_events()` or config-driven

## Common Tasks

### Adding Device Support
1. Update `config.json` with new device serial (use `print_discovered_objects()` to find serials)
2. Access via `v.devices["device_name"]` after initialization

### Extending Device Methods
- Add new methods to `vr_tracked_device` class (e.g., custom sensor queries)
- Follow existing pattern: query via `self.vr.get*Property()` or `get_pose()`

### Network Integration
- `udp_emitter.py` shows pattern for sending pose data over UDP
- Can extend to include Euler angles, velocity, or button state
