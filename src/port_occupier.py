"""
@file  port_occupier.py
@brief 查找并打印占用指定 UDP 端口的进程信息。
@details
对应 C++ 实现：
  MotionGloveSDK/src/motionGloveSDK.cpp - MotionGloveSDK_PrintUDPPortOccupier()

支持平台：Windows / Linux
  Windows : netstat -ano -p udp + tasklist
  Linux   : lsof -nP -iUDP:<port>，回退到 ss -lunp

只读探测，不修改系统状态；shell 调用失败时静默返回空列表。

调用方式：
  from port_occupier import print_udp_port_occupier

  print_udp_port_occupier(5001)
"""

import subprocess
import sys


def _run(cmd: str) -> str:
    """@brief 运行 shell 命令并返回标准输出。

    @param cmd 要执行的 shell 命令行字符串。
    @return 标准输出文本；执行失败/超时返回空字符串（不抛异常）。
    """
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=5
        )
        return result.stdout
    except Exception:
        return ""


def _find_occupier_windows(port: int) -> list[str]:
    """@brief Windows 实现：netstat 找 PID + tasklist 找进程名。

    @details 对应 C++ #ifdef _WIN32 分支。
    @param port 要查询的 UDP 端口号，1~65535。
    @return 描述行列表，每行一条记录；未找到占用者时为空列表。
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
    """@brief Linux 实现：优先 lsof，失败回退 ss。

    @details 对应 C++ #else 分支。
    @param port 要查询的 UDP 端口号，1~65535。
    @return 描述行列表；未找到占用者时为空列表。
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
    """@brief 查找占用指定 UDP 端口的进程（按平台分派）。

    @param port UDP 端口号，1~65535。
    @return 描述行列表；每条记录说明一个占用进程；未找到任何占用者时返回空列表。
    """
    if sys.platform == "win32":
        return _find_occupier_windows(port)
    else:
        return _find_occupier_linux(port)


def print_udp_port_occupier(port: int) -> None:
    """@brief 查找并打印占用指定 UDP 端口的进程信息。

    @details 对应 C++ MotionGloveSDK_PrintUDPPortOccupier()。
    @param port UDP 端口号，1~65535。
    @return 无（None）。
    """
    results = find_udp_port_occupier(port)
    if results:
        for line in results:
            print(f"[端口占用] {line}")
    else:
        print(f"[端口占用] 未找到占用端口 {port} 的进程")
