"""
port_occupier.py - MotionGloveSDK Python
查找并打印占用指定 UDP 端口的进程信息

对应 C++ 实现：
  MotionGloveSDK/src/motionGloveSDK.cpp - MotionGloveSDK_PrintUDPPortOccupier()

支持平台：Windows / Linux
  Windows : netstat -ano -p udp + tasklist
  Linux   : lsof -nP -iUDP:<port>，回退到 ss -lunp

调用方式：
  from port_occupier import print_udp_port_occupier

  print_udp_port_occupier(5001)
"""

import subprocess
import sys


def _run(cmd: str) -> str:
    """运行 shell 命令，返回标准输出字符串；失败返回空字符串。"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=5
        )
        return result.stdout
    except Exception:
        return ""


def _find_occupier_windows(port: int) -> list[str]:
    """
    Windows 实现：
      1. netstat -ano -p udp | findstr :<port>  → 提取 PID
      2. tasklist /FI "PID eq <pid>"            → 获取进程名
    对应 C++ #ifdef _WIN32 分支。
    返回描述行列表，每行一条记录。
    """
    lines: list[str] = []

    output = _run(f"netstat -ano -p udp | findstr :{port}")
    if not output.strip():
        return lines

    # 从 netstat 输出中提取 PID（每行最后一列）
    pids: set[str] = set()
    for line in output.splitlines():
        parts = line.split()
        if parts:
            last = parts[-1]
            if last.isdigit():
                pids.add(last)

    if not pids:
        lines.append(f"端口 {port} 被占用，但 netstat 未找到进程信息")
        return lines

    for pid in sorted(pids):
        task_out = _run(f'tasklist /FI "PID eq {pid}" /FO CSV /NH')
        task_out = task_out.strip()
        if task_out:
            # CSV 格式："python.exe","12345","Console","1","xx,xxx K"
            name = task_out.split(",")[0].strip('"')
            lines.append(f"端口 {port} 被占用  PID={pid}  进程名={name}")
        else:
            lines.append(f"端口 {port} 被占用  PID={pid}  (进程名未找到)")

    return lines


def _find_occupier_linux(port: int) -> list[str]:
    """
    Linux 实现：先尝试 lsof，回退到 ss。
    对应 C++ #else 分支。
    返回描述行列表。
    """
    lines: list[str] = []

    # 优先使用 lsof
    output = _run(f"lsof -nP -iUDP:{port} 2>/dev/null")
    if output.strip():
        for line in output.strip().splitlines():
            lines.append(f"端口 {port} 被占用  {line}")
        return lines

    # 回退到 ss
    output = _run(f"ss -lunp 'sport = :{port}' 2>/dev/null")
    if output.strip():
        for line in output.strip().splitlines():
            lines.append(f"端口 {port} 被占用  {line}")
        return lines

    lines.append(f"端口 {port} 被占用，但 lsof/ss 未找到进程信息")
    return lines


def find_udp_port_occupier(port: int) -> list[str]:
    """
    查找占用指定 UDP 端口的进程。

    参数：
      port : UDP 端口号

    返回：
      描述行列表；每条记录说明一个占用进程。
      若未找到任何占用者，返回空列表。
    """
    if sys.platform == "win32":
        return _find_occupier_windows(port)
    else:
        return _find_occupier_linux(port)


def print_udp_port_occupier(port: int) -> None:
    """
    查找并打印占用指定 UDP 端口的进程信息。
    对应 C++ MotionGloveSDK_PrintUDPPortOccupier()。
    """
    results = find_udp_port_occupier(port)
    if results:
        for line in results:
            print(f"[端口占用] {line}")
    else:
        print(f"[端口占用] 未找到占用端口 {port} 的进程")
