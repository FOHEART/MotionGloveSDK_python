"""
@file  status_cmd.py
@brief status 命令：后端/原生库/会话/GUI 加载状态探测。
@details status 是探测命令，即使原生库缺失也返回成功信封，
         由 data.native_available 告知 Agent，避免探测本身变成错误。
"""

from __future__ import annotations

import platform
import socket
import sys
from typing import Any

from src import motionGloveSDK as sdk

from .. import session
from ..envelope import APP_NAME, CLI_VERSION, PROTOCOL_VERSION
from . import ACTION_NAMES

Result = tuple[dict[str, Any], str]


def _probe_port(port: int) -> bool:
    """@brief 试探 UDP 端口是否已被占用（True=占用）。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("0.0.0.0", port))
        return False
    except OSError:
        return True
    finally:
        sock.close()


def status(payload: dict[str, Any]) -> Result:
    """@brief 返回 CLI 与 SDK 的完整运行状态。

    @param payload 未使用（保留以统一 handler 签名）。
    @return (data, message)。
    """
    try:
        backend = sdk.MotionGloveSDK_GetBackendName()
    except Exception:
        backend = "unknown"

    try:
        available = bool(sdk.MotionGloveSDK_IsAvailable())
    except Exception:
        available = False

    library: str | None = None
    native_version: int | None = None
    if available:
        try:
            library = sdk.MotionGloveSDK_GetNativeLibraryPath()
        except Exception:
            library = None
        try:
            native_version = int(sdk.MotionGloveSDK_getVersion())
        except Exception:
            native_version = None

    project = session.summary()
    port = int(project.get("port") or 5001)
    data: dict[str, Any] = {
        "app": APP_NAME,
        "cli_version": CLI_VERSION,
        "protocol": PROTOCOL_VERSION,
        "backend": backend,
        "native_available": available,
        "native_library": library,
        "native_version": native_version,
        "python": platform.python_version(),
        "platform": sys.platform,
        # 证明 --cli 分流没有实例化任何 GUI 框架对象
        "gui_loaded": ("vtk" in sys.modules or "PySide6" in sys.modules),
        "project": project,
        "udp_port": port,
        "udp_port_in_use": _probe_port(port),
        "session_file": str(session.SESSION_FILE),
        "actions": list(ACTION_NAMES),
    }
    return data, "状态查询成功"
