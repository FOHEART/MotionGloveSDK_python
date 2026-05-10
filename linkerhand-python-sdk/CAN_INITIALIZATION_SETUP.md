# CAN Interface Auto-Initialization - Quick Start

## What Was Done (已完成的工作)

The following changes have been made to automatically execute the CAN initialization command (`sudo /usr/sbin/ip link set can0 up type can bitrate 1000000`) before running the program:

已进行以下更改以在运行程序之前自动执行 CAN 初始化命令：

### 1. **New Python Module** (新的 Python 模块)
   - **File**: `LinkerHand/utils/setup_can_interface.py`
   - **Features**:
     - `SetupCANInterface` class for CAN setup and verification
     - `initialize_can_interface()` function for quick usage
     - Cross-platform support (Linux/Windows)
     - Automatic sudo password handling

### 2. **Modified GUI Application** (修改的 GUI 应用)
   - **File**: `example/gui_control/gui_control.py`
   - **Changes**: Automatically initializes CAN when the application starts
   - **Impact**: No manual command needed before running the GUI

### 3. **Standalone Setup Script** (独立初始化脚本)
   - **File**: `example/gui_control/src/init_can.py`
   - **Usage**: Can be run manually to initialize CAN before any application
   - **Command**: `python3 example/gui_control/src/init_can.py`

### 4. **Documentation** (文档)
   - **File**: `CAN_SETUP_GUIDE.md`
   - **Content**: Comprehensive guide with examples and troubleshooting

## How to Use (使用方法)

### Option 1: Run GUI Normally (正常运行 GUI)
The CAN interface will be automatically initialized:
```bash
python3 example/gui_control/gui_control.py
```

### Option 2: Pre-initialize CAN (预先初始化 CAN)
Run the setup script first:
```bash
python3 example/gui_control/src/init_can.py
```
Then run your application:
```bash
python3 example/gui_control/gui_control.py
```

### Option 3: In Your Own Code (在自己的代码中使用)
```python
from LinkerHand.utils.setup_can_interface import initialize_can_interface

# Initialize CAN
initialize_can_interface()

# Your LinkerHand code here
```

## Configuration (配置)

The CAN interface settings are configured in `LinkerHand/config/setting.yaml`:

```yaml
LINKER_HAND:
  LEFT_HAND:
    CAN: "can0"  # Change if using different interface
    MODBUS: "None"  # For RS485 mode, set to "/dev/ttyUSB0"

PASSWORD: "12345678"  # Your Linux system password
```

**Important**: Update the `PASSWORD` field with your actual system password!

## What Happens (工作流程)

When the program starts:

1. **Detection** - System detects OS (Linux/Windows)
2. **Check** - Checks if CAN interface is already UP
3. **Setup** - If not UP, executes: `sudo /usr/sbin/ip link set can0 up type can bitrate 1000000`
4. **Verify** - Confirms the interface is now UP
5. **Continue** - Proceeds with application startup

## Verification (验证)

After running, you should see messages like:
```
Initializing CAN interface...
CAN interface 'can0' initialized successfully
CAN interface 'can0' is UP
```

Or if already initialized:
```
CAN interface 'can0' is already up
```

## Troubleshooting (故障排除)

See `CAN_SETUP_GUIDE.md` for detailed troubleshooting information.

### Quick Fixes (快速修复)

**If password fails:**
- Update `PASSWORD` in `LinkerHand/config/setting.yaml` with your correct system password
- Or use: `sudo python3 example/gui_control/gui_control.py`

**If CAN still fails:**
- Try manual setup: `sudo /usr/sbin/ip link set can0 up type can bitrate 1000000`
- Verify USB-to-CAN adapter is connected

**On Windows:**
- CAN initialization is skipped (use PCAN drivers)
- Application will work normally

## Reverting Changes (恢复更改)

If you want to remove the auto-initialization:

1. Open `example/gui_control/gui_control.py`
2. Remove the import line:
   ```python
   from LinkerHand.utils.setup_can_interface import initialize_can_interface
   ```
3. Remove these lines from the `main()` function:
   ```python
   ColorMsg(msg="Initializing CAN interface...", color="yellow")
   if not initialize_can_interface(can_interface="can0", bitrate=1000000):
       ColorMsg(msg="Warning: CAN interface initialization failed, continuing anyway...", color="yellow")
   ```

## Files Summary (文件总结)

| File | Status | Purpose |
|------|--------|---------|
| `LinkerHand/utils/setup_can_interface.py` | ✅ Created | Core CAN initialization module |
| `example/gui_control/src/init_can.py` | ✅ Created | Standalone setup script |
| `example/gui_control/gui_control.py` | ✅ Modified | Auto-initialize on startup |
| `CAN_SETUP_GUIDE.md` | ✅ Created | Comprehensive documentation |

## Next Steps (后续步骤)

1. Update `PASSWORD` in `LinkerHand/config/setting.yaml`
2. Test by running: `python3 example/gui_control/gui_control.py`
3. Refer to `CAN_SETUP_GUIDE.md` for advanced usage

---

For more information, see:
- [CAN_SETUP_GUIDE.md](CAN_SETUP_GUIDE.md) - Comprehensive guide
- [doc/API-Reference.md](doc/API-Reference.md) - API documentation
- [README.md](README.md) - Project overview
