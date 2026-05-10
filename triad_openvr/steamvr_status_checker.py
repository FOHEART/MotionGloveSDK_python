"""SteamVR 进程状态检查模块

功能：
- 定期检查系统中 SteamVR 进程是否运行
- 提供状态改变回调
- 跨平台支持 (Windows, Linux, macOS)
"""

import subprocess
import platform
from typing import Callable, Optional
from PySide6.QtCore import QTimer


# 调试开关，默认关闭打印
DEBUG = False


def _debug_print(tag: str, message: str):
    """带标签的调试打印（受DEBUG开关控制）。"""
    if DEBUG:
        print(f"[{tag}] {message}")


class SteamVRStatusChecker:
    """SteamVR 进程状态检查器，使用 QTimer 定期检查。"""
    
    def __init__(self, check_interval: int = 1000):
        """初始化 SteamVR 状态检查器。
        
        Args:
            check_interval: 检查间隔，单位毫秒，默认 1000ms（每秒一次）
        """
        self._timer = QTimer()
        self._timer.timeout.connect(self._on_timer)
        self._check_interval = check_interval
        
        self._last_status: Optional[bool] = None
        self._status_changed_callback: Optional[Callable[[bool], None]] = None
        
        _debug_print("SteamVRStatusChecker", f"初始化，检查间隔: {check_interval}ms")
    
    def start(self):
        """启动状态检查定时器。"""
        _debug_print("SteamVRStatusChecker", "启动定时器")
        self._timer.setInterval(self._check_interval)
        self._timer.start()
    
    def stop(self):
        """停止状态检查定时器。"""
        _debug_print("SteamVRStatusChecker", "停止定时器")
        self._timer.stop()
    
    def is_running(self) -> bool:
        """检查定时器是否运行。"""
        return self._timer.isActive()
    
    def set_status_changed_callback(self, callback: Callable[[bool], None]):
        """设置状态改变回调函数。
        
        Args:
            callback: 当 SteamVR 状态改变时调用，参数为 True（已启动）或 False（未启动）
        """
        self._status_changed_callback = callback
        _debug_print("SteamVRStatusChecker", "设置状态改变回调")
    
    def _on_timer(self):
        """定时器回调，执行状态检查。"""
        _debug_print("SteamVRStatusChecker", "执行定时检查...")
        current_status = self._check_steamvr_running()
        _debug_print("SteamVRStatusChecker", f"检查结果: {current_status}, 上次状态: {self._last_status}")
        
        # 如果状态改变，触发回调
        if current_status != self._last_status:
            _debug_print("SteamVRStatusChecker", f"状态已改变: {current_status}")
            self._last_status = current_status
            if self._status_changed_callback:
                self._status_changed_callback(current_status)
        else:
            _debug_print("SteamVRStatusChecker", f"状态未改变: {current_status}")
    
    @staticmethod
    def _check_steamvr_running() -> bool:
        """检查系统中 SteamVR 进程是否运行。
        
        Returns:
            True 如果 SteamVR 正在运行，False 否则
        """
        try:
            system = platform.system()
            _debug_print("Check", f"检查系统: {system}")
            
            if system == "Windows":
                # Windows: 查找 vrserver.exe 进程
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq vrserver.exe"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                running = "vrserver.exe" in result.stdout
                _debug_print("Check", f"Windows tasklist 结果: {running}")
                return running
            elif system == "Linux":
                # Linux: 首先尝试 pgrep，失败则使用 ps
                _debug_print("Check", "尝试 pgrep -f vrserver...")
                try:
                    result = subprocess.run(
                        ["pgrep", "-f", "vrserver"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    _debug_print("Check", f"pgrep 返回码: {result.returncode}")
                    _debug_print("Check", f"pgrep 输出: {result.stdout}")
                    if result.returncode == 0:
                        _debug_print("Check", "pgrep 找到 vrserver 进程")
                        return True
                except Exception as e:
                    _debug_print("Check", f"pgrep 异常: {e}")
                
                # 备选方案：使用 ps 命令查找进程
                _debug_print("Check", "尝试 ps aux | grep vrserver...")
                try:
                    result = subprocess.run(
                        ["ps", "aux"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    lines = result.stdout.split('\n')
                    vrserver_lines = [l for l in lines if 'vrserver' in l]
                    _debug_print("Check", f"ps 找到 {len(vrserver_lines)} 行含 'vrserver' 的进程:")
                    for line in vrserver_lines[:3]:  # 只打印前3行
                        _debug_print("Check", f"  {line}")
                    found = "vrserver" in result.stdout
                    _debug_print("Check", f"ps 检查结果: {found}")
                    return found
                except Exception as e:
                    _debug_print("Check", f"ps 异常: {e}")
                    return False
            elif system == "Darwin":
                # macOS: 首先尝试 pgrep，失败则使用 ps
                _debug_print("Check", "尝试 pgrep -f vrserver...")
                try:
                    result = subprocess.run(
                        ["pgrep", "-f", "vrserver"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    _debug_print("Check", f"pgrep 返回码: {result.returncode}")
                    if result.returncode == 0:
                        _debug_print("Check", "pgrep 找到 vrserver 进程")
                        return True
                except Exception as e:
                    _debug_print("Check", f"pgrep 异常: {e}")
                
                # 备选方案：使用 ps 命令查找进程
                _debug_print("Check", "尝试 ps aux | grep vrserver...")
                try:
                    result = subprocess.run(
                        ["ps", "aux"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    found = "vrserver" in result.stdout
                    _debug_print("Check", f"ps 检查结果: {found}")
                    return found
                except Exception as e:
                    _debug_print("Check", f"ps 异常: {e}")
                    return False
            else:
                # 未知系统
                _debug_print("Check", f"未知系统: {system}")
                return False
        except Exception as e:
            # 发生异常时，认为 SteamVR 未运行
            _debug_print("Check", f"外层异常: {e}")
            return False


def set_debug(enabled: bool):
    """全局设置是否打印调试信息。
    
    Args:
        enabled: True 打印调试信息，False 关闭调试信息
    """
    global DEBUG
    DEBUG = enabled
