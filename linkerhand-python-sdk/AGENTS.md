# LinkerHand-Python-SDK: Agent Guidelines

**Project**: Python SDK for controlling dexterous robotic hands (O6, L6, L7, L10, L20, G20, L21, L25)  
**Language**: Python 3.8+  
**Key Technologies**: CAN/RS485 communication, PyQt5 GUI, robotics simulation (MUJOCO, Sapien)

## Quick Start

### Main Entry Point
- **`LinkerHand/linker_hand_api.py`** - Primary API class `LinkerHandApi` for all hand control
- Initialize: `LinkerHandApi(hand_type="left", hand_joint="L10", modbus="None", can="can0")`

### Configuration
- **`LinkerHand/config/setting.yaml`** - Configure hand models, communication protocol, CAN/RS485 ports
  - `LINKER_HAND.LEFT_HAND.JOINT` - Set hand model (O6/L6/L7/L10/L20/G20/L21/L25)
  - `MODBUS` - Set to "None" for CAN, or "/dev/ttyUSB*" for RS485 (Linux only)
  - `CAN` - CAN interface (default "can0" on Linux, "PCAN_USBBUS1" on Windows)

### Common API Methods
| Method | Purpose | Example |
|--------|---------|---------|
| `finger_move(pose=[...])` | Set finger positions (0-255 range) | `hand.finger_move([100,120,110,105,100,...])` |
| `set_speed(speed=[...])` | Set joint speeds | `hand.set_speed([100,150,120,130,140])` |
| `set_torque(torque=[...])` | Set force/torque limits | `hand.set_torque([180,100,80,99,255])` |
| `set_current(current=[...])` | Set motor current values | `hand.set_current([99,72,80,66,20])` |
| `get_finger_pose()` | Read current finger positions | Returns list of position values |
| `get_force()` | Read force/pressure sensor data | Returns force values if available |
| `get_speed()` | Read current joint speeds | Returns speed values |

## Project Structure

```
LinkerHand/
├── linker_hand_api.py          # Main API - start here
├── core/
│   ├── can/                    # CAN protocol implementations per hand model
│   │   ├── linker_hand_*_can.py
│   └── rs485/                  # RS485/MODBUS implementations
│       └── linker_hand_*_rs485.py
├── config/
│   ├── setting.yaml            # Primary configuration file
│   └── *_positions.yaml        # Preset positions per hand model
└── utils/
    ├── load_write_yaml.py      # YAML configuration handler
    ├── mapping.py              # Protocol message mappings
    └── open_can.py             # CAN interface setup (Linux)

example/
├── gui_control/                # PyQt5-based interactive control GUI
│   ├── gui_control.py
│   └── views/                  # GUI components
├── L10/                        # Examples for L10 hand
│   ├── gesture/                # Predefined gestures (fist, open palm, etc.)
│   ├── get_status/             # Reading sensor data
│   └── grab/                   # Grasping examples
└── [L6, L7, L24]/              # Similar structure for other models

simulation/
├── linker_hand_mujoco/         # MUJOCO simulation
└── Linker_hand_Sapien/         # Sapien simulation
```

## Hand Models and Joint Counts

| Model | DOF | Protocol Support | Typical Use |
|-------|-----|------------------|------------|
| O6 | 6 | CAN, RS485 | Research hand |
| L6 | 6 | CAN, RS485 | Dexterous tasks |
| L7 | 7 | CAN, RS485 | L6 with wrist rotation |
| L10 | 10 | CAN only | Enhanced dexterity |
| L20 | 20 | CAN only | High dexterity |
| L21 | 21 | CAN only | L20 variant |
| L25 | 25 | CAN only | Maximum dexterity |
| G20 | 20 | CAN only | Industrial version |

## Common Development Patterns

### 1. Creating a New Gesture Example
```python
#!/usr/bin/env python3
import sys, os
current_dir = os.path.dirname(os.path.abspath(__file__))
target_dir = os.path.abspath(os.path.join(current_dir, "../../.."))
sys.path.append(target_dir)

from LinkerHand.linker_hand_api import LinkerHandApi

hand = LinkerHandApi(hand_joint="L10", hand_type="left", can="can0")
hand.set_speed([100, 150, 150, 150, 150])
pose = [60, 60, 80, 80, 80, 80, 80, 80, 80, 80]  # L10 requires 10 values
hand.finger_move(pose=pose)
```

### 2. Hand Model-Specific Logic
- **O6/L6**: 6 joint values
- **L7**: 7 joint values
- **L10**: 10 joint values
- **L20/L25/G20**: 20+ joint values
- Always check `hand.hand_joint` to determine DOF requirements

### 3. Communication Setup
**CAN (Linux)**:
```bash
sudo ip link set can0 up type can bitrate 1000000  # Setup CAN
python3 example_script.py
```

**RS485 (Linux)**:
```bash
sudo chmod 777 /dev/ttyUSB0  # Grant permissions
pip install minimalmodbus pymodbus pyserial
python3 example_script.py  # Script uses modbus parameter
```

**Windows CAN**:
- Use `PCAN_USBBUS1` instead of `can0` in config
- PCAN driver required

### 4. Configuration Best Practices
- Always read `setting.yaml` before initialization
- Modify `LINKER_HAND.LEFT_HAND.JOINT` for different hand models
- For RS485, set `MODBUS: "/dev/ttyUSB0"` and `CAN: "None"` won't work (use "can0" placeholder)
- Joint positions (0-255 range) correspond to actual finger positions

## Important Conventions

1. **Position Range**: All finger positions use 0-255 scale (not 0-1 or radians)
2. **Path Setup**: Examples add workspace root to `sys.path` for imports
3. **Color Output**: Use `ColorMsg(msg="...", color="green"|"red"|"yellow")` for console output
4. **Hardware Check**: SDK verifies hardware version on startup; warnings indicate connection issues
5. **Hand ID**: Left hand = 0x28, Right hand = 0x27 (internal)

## Example Usage by Task

### Reading Sensor Data
See [example/L10/get_status/](example/L10/get_status/) for:
- `get_force.py` - Force/pressure readings
- `get_status.py` - State and position readings
- `get_speed.py` - Speed readings

### Controlling GUI
See [example/gui_control/gui_control.py](example/gui_control/) - Interactive sliders and visualization

### Predefined Gestures
See [example/L10/gesture/](example/L10/gesture/) for gesture examples:
- `linker_hand_fist.py`
- `linker_hand_open_palm.py`
- `linker_hand_opposition.py`
- `linker_hand_sway.py`

## Troubleshooting Tips

- **"CAN interface is not open"**: CAN not initialized. Run `sudo ip link set can0 up type can bitrate 1000000`
- **"Hardware version number not recognized"**: USB-CAN disconnected; try reinserting
- **Import errors in examples**: Check that workspace root is added to `sys.path` correctly
- **Position values not working**: Verify hand model matches pose list length (e.g., L10 needs 10 values, not 6)
- **RS485 port not found**: Check `/dev` directory for USB device (typically `/dev/ttyUSB0`)

## API Reference
See [doc/API-Reference.md](doc/API-Reference.md) for complete method documentation
