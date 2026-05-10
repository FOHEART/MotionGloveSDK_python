# CAN Auto-Initialization - Quick Reference Card
# CAN 自动初始化 - 快速参考卡

## Before & After (对比)

### ❌ Before (之前)
```bash
# Step 1: Manual CAN initialization
sudo /usr/sbin/ip link set can0 up type can bitrate 1000000

# Step 2: Run GUI
python3 example/gui_control/gui_control.py
```

### ✅ After (之后)
```bash
# Just run - CAN initializes automatically!
python3 example/gui_control/gui_control.py
```

---

## Quick Start (快速开始)

### 1️⃣ Update Configuration
```bash
# Edit this file
nano LinkerHand/config/setting.yaml

# Change the password to your system password
PASSWORD: "your_actual_password"  # ← Update this!
```

### 2️⃣ Test the Setup (Optional)
```bash
python3 test_can_setup.py
```

### 3️⃣ Run Your Application
```bash
# GUI will auto-initialize CAN
python3 example/gui_control/gui_control.py

# Or use standalone setup script
python3 example/gui_control/src/init_can.py
```

---

## In Your Own Code (在自己的代码中)

```python
from LinkerHand.utils.setup_can_interface import initialize_can_interface

# At the beginning of your script
initialize_can_interface()

# Your LinkerHand code here
from LinkerHand.linker_hand_api import LinkerHandApi
hand = LinkerHandApi(hand_joint="L10", hand_type="left")
```

---

## Troubleshooting (故障排除)

| Problem | Solution |
|---------|----------|
| "Permission denied" | Update password in setting.yaml or use: `sudo python3 gui_control.py` |
| "CAN interface not found" | Verify USB adapter is connected and CAN name in setting.yaml |
| "Hardware version not recognized" | CAN might not be initialized. Run: `sudo /usr/sbin/ip link set can0 up type can bitrate 1000000` manually |
| "Command not found: /usr/sbin/ip" | Rare on Linux. Check system PATH. |

---

## Files Modified/Created (修改/创建的文件)

| File | Type | Status | Purpose |
|------|------|--------|---------|
| `LinkerHand/utils/setup_can_interface.py` | 🆕 New | ✅ Created | Core CAN setup module |
| `example/gui_control/gui_control.py` | 📝 Modified | ✅ Updated | Auto-init on startup |
| `example/gui_control/src/init_can.py` | 🆕 New | ✅ Created | Standalone setup script |
| `test_can_setup.py` | 🆕 New | ✅ Created | Verification script |
| `CAN_INITIALIZATION_SETUP.md` | 📖 Doc | ✅ Created | Quick start guide |
| `CAN_SETUP_GUIDE.md` | 📖 Doc | ✅ Created | Full documentation |
| `IMPLEMENTATION_SUMMARY.md` | 📖 Doc | ✅ Created | Technical details |

---

## Configuration (配置)

**File**: `LinkerHand/config/setting.yaml`

```yaml
VERSION: 3.1.0
LINKER_HAND:
  LEFT_HAND:
    CAN: "can0"              # Interface name
    MODBUS: "None"           # "None"=CAN, "/dev/ttyUSB0"=RS485
    JOINT: L10               # Hand model
PASSWORD: "your_password"    # ← UPDATE THIS!
```

---

## Common Commands (常用命令)

### Test Setup
```bash
python3 test_can_setup.py
```

### Manual CAN Init
```bash
sudo /usr/sbin/ip link set can0 up type can bitrate 1000000
```

### Check CAN Status
```bash
ip link show can0
cat /sys/class/net/can0/operstate
```

### Run GUI (Auto-init)
```bash
python3 example/gui_control/gui_control.py
```

### Run Setup Only
```bash
python3 example/gui_control/src/init_can.py
```

---

## Documentation (文档)

- **Quick Start**: [CAN_INITIALIZATION_SETUP.md](CAN_INITIALIZATION_SETUP.md)
- **Full Guide**: [CAN_SETUP_GUIDE.md](CAN_SETUP_GUIDE.md)
- **Technical**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **SDK Guide**: [AGENTS.md](AGENTS.md)

---

## Key Features (主要特性)

✅ **Automatic** - No manual setup needed  
✅ **Smart** - Detects if already initialized  
✅ **Safe** - Won't interrupt if already running  
✅ **Fast** - Minimal startup overhead  
✅ **Backward Compatible** - All existing code works  
✅ **Cross-Platform** - Linux & Windows support  

---

## Security (安全)

🔐 **Password in Config**
```bash
# Restrict access to config file
chmod 600 LinkerHand/config/setting.yaml
```

🔐 **Optional: Passwordless Sudo**
Add to `/etc/sudoers`:
```
your_username ALL=(ALL) NOPASSWD: /usr/sbin/ip link set can0 up type can bitrate 1000000
```

---

## Support (支持)

❓ **Questions?**
1. Check the documentation files above
2. Run `test_can_setup.py` to verify setup
3. Ensure password in `setting.yaml` is correct

---

**Version**: 1.0  
**Date**: May 6, 2026  
**Status**: ✅ Complete and Tested
