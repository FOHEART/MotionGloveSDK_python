# CAN Interface Auto-Initialization Guide
# CAN 接口自动初始化指南

## Overview (概述)

This guide explains the automatic CAN interface initialization system added to the LinkerHand Python SDK. The system automatically executes the command `sudo /usr/sbin/ip link set can0 up type can bitrate 1000000` before running applications on Linux systems.

本指南说明了添加到 LinkerHand Python SDK 的自动 CAN 接口初始化系统。该系统在 Linux 系统上运行应用程序之前自动执行命令 `sudo /usr/sbin/ip link set can0 up type can bitrate 1000000`。

## Files Added (添加的文件)

### 1. Core Module (核心模块)
- **Location**: `LinkerHand/utils/setup_can_interface.py`
- **Purpose**: Contains `SetupCANInterface` class and `initialize_can_interface()` function
- **Features**:
  - Automatic CAN interface detection
  - Cross-platform support (Linux/Windows)
  - Status verification
  - Error handling and reporting

### 2. Setup Script (初始化脚本)
- **Location**: `example/gui_control/src/init_can.py`
- **Purpose**: Standalone script for manual CAN initialization
- **Usage**: Can be run before launching the GUI

### 3. Modified GUI Application (修改的 GUI 应用程序)
- **File**: `example/gui_control/gui_control.py`
- **Changes**: Added automatic CAN initialization at startup
- **Behavior**: Attempts to initialize CAN before creating GUI window

## Configuration (配置)

The CAN interface name and password are read from `LinkerHand/config/setting.yaml`:

```yaml
LINKER_HAND:
  LEFT_HAND:
    CAN: "can0"  # CAN interface name
    MODBUS: "None"  # Set to device path for RS485, or "None" for CAN

PASSWORD: "12345678"  # Linux system password for sudo
```

## Usage Methods (使用方法)

### Method 1: Automatic Initialization via GUI (GUI 自动初始化)

Simply run the GUI application:
```bash
python3 example/gui_control/gui_control.py
```

The CAN interface will be automatically initialized before the GUI window appears.

### Method 2: Manual Initialization Script (手动初始化脚本)

Run the setup script separately:
```bash
python3 example/gui_control/src/init_can.py
```

This can be used to verify CAN setup before running other applications.

### Method 3: Programmatic Usage (编程方式)

Use in your own Python scripts:

```python
from LinkerHand.utils.setup_can_interface import initialize_can_interface

# Initialize CAN interface
if initialize_can_interface(can_interface="can0"):
    print("CAN interface ready")
else:
    print("Failed to initialize CAN interface")
```

### Method 4: Advanced Usage (高级用法)

For more control, use the `SetupCANInterface` class directly:

```python
from LinkerHand.utils.setup_can_interface import SetupCANInterface

setup = SetupCANInterface()

# Setup CAN
if setup.setup_can("can0", bitrate=1000000):
    # Verify CAN
    if setup.verify_can_interface("can0"):
        print("CAN interface is ready")
```

## How It Works (工作原理)

### 1. Linux System (Linux 系统)

When the system detects a Linux environment:

```python
# Check if CAN interface is already UP
ip link show can0

# If not, activate it with sudo
sudo /usr/sbin/ip link set can0 up type can bitrate 1000000

# Verify interface state
cat /sys/class/net/can0/operstate
```

### 2. Windows System (Windows 系统)

On Windows systems, CAN initialization is skipped (handled by PCAN drivers).

### 3. RS485 Mode (RS485 模式)

If `MODBUS` is set to a device path (not "None"), CAN initialization is skipped and RS485 is used instead.

## Error Handling (错误处理)

The system provides graceful error handling:

- **CAN already UP**: No action needed, continues normally
- **CAN setup fails**: Warnings are displayed, application continues
- **No sudo password**: Falls back to attempting unprivileged access
- **File/command not found**: Clear error message provided

## Output Examples (输出示例)

### Successful Initialization (成功初始化)

```
Initializing CAN interface...
CAN interface 'can0' initialized successfully
CAN interface 'can0' is UP
```

### Already Initialized (已初始化)

```
Initializing CAN interface...
CAN interface 'can0' is already up
```

### RS485 Mode (RS485 模式)

```
RS485 (MODBUS) mode detected, CAN initialization skipped.
To use RS485: grant permissions with: sudo chmod 777 /dev/ttyUSB0
```

## Troubleshooting (故障排除)

### Issue: "CAN interface is not open"
**Solution**: Check that:
1. CAN adapter is connected via USB
2. Setting `MODBUS: "None"` in setting.yaml
3. Password in setting.yaml is correct

### Issue: Permission Denied
**Solution**: Ensure the password in `setting.yaml` matches your system password:
```yaml
PASSWORD: "your_password"  # Replace with your actual password
```

### Issue: "/usr/sbin/ip command not found"
**Solution**: This is rare on Linux systems. Verify system PATH or use full path.

### Issue: Still Need Manual Setup
**Workaround**: If automatic setup fails, run manually before your application:
```bash
sudo /usr/sbin/ip link set can0 up type can bitrate 1000000
```

## Backward Compatibility (向后兼容性)

- Existing code continues to work unchanged
- CAN initialization is optional (non-fatal if it fails)
- Can be disabled by removing the `initialize_can_interface()` call from `gui_control.py`

## Security Notes (安全说明)

- **Password Storage**: The password in `setting.yaml` is stored in plain text. Ensure file permissions are restricted:
  ```bash
  chmod 600 LinkerHand/config/setting.yaml
  ```
- **Sudo Configuration**: Consider configuring passwordless sudo for the specific `ip` command in `/etc/sudoers`:
  ```
  your_username ALL=(ALL) NOPASSWD: /usr/sbin/ip link set can0 up type can bitrate 1000000
  ```

## API Reference (API 参考)

### initialize_can_interface()

```python
def initialize_can_interface(can_interface="can0", bitrate=1000000, verify=True):
    """
    Args:
        can_interface (str): CAN interface name, default "can0"
        bitrate (int): CAN bitrate, default 1000000
        verify (bool): Whether to verify interface state, default True
        
    Returns:
        bool: True if successful, False if failed
    """
```

### SetupCANInterface class

```python
class SetupCANInterface:
    def setup_can(self, can_interface="can0", bitrate=1000000) -> bool
    def verify_can_interface(self, can_interface="can0") -> bool
```

## Logs and Debugging (日志和调试)

The system uses the `ColorMsg` utility for colored output:
- **Green**: Success messages
- **Yellow**: Warnings and information
- **Red**: Error messages

To see detailed subprocess output during development, modify the `capture_output=True` parameter in `setup_can_interface.py`.
