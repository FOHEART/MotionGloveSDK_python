"""
@file  envelope.py
@brief CLI-Anything 统一输出信封与错误码定义。
@details
所有命令输出统一为 {"ok":bool,"code":int,"message":str,"data":{}}，
data 永远存在（可为空对象）。进程退出码只区分成败（0/1），
细分错误码放在信封的 code 字段中传递，避免 Windows 下负退出码被
Python 读成 4294967294 这类无符号值。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

APP_NAME = "MotionGlove3DViewer"
CLI_VERSION = "1.0.0"
PROTOCOL_VERSION = "1.0"

# ── 错误码表（同步维护于仓库根 SKILL.md）────────────────────────────────
OK = 0            # 成功
ERR_USAGE = 1     # 参数/用法错误：未知命令、缺必填项、非法值、非法 payload JSON
ERR_STATE = 2     # 会话状态不满足：未打开工程
ERR_IO = 3        # IO 错误：文件不存在、目录不存在、写出失败
ERR_PARSE = 4     # 数据解析错误：CSV 无可用帧、索引越界
ERR_NATIVE = 5    # 原生库不可用 / ABI 不匹配
ERR_UDP = 6       # UDP 错误：绑定失败、等待帧超时
ERR_EXPORT = 7    # 导出格式或目标不支持
ERR_INTERNAL = 8  # 未预期的内部错误（命令实现抛出的非 CliError 异常）

ERROR_CODES: dict[int, str] = {
    OK: "成功",
    ERR_USAGE: "参数/用法错误",
    ERR_STATE: "会话状态不满足",
    ERR_IO: "IO 错误",
    ERR_PARSE: "数据解析错误",
    ERR_NATIVE: "原生库不可用",
    ERR_UDP: "UDP 错误",
    ERR_EXPORT: "导出格式/目标不支持",
    ERR_INTERNAL: "内部错误",
}


class CliError(Exception):
    """@brief 命令级业务错误基类。

    @details 命令实现只抛本类（或其子类），由分发器捕获并转成失败信封。
             命令内严禁调用 sys.exit() / argparse 的出错即退出行为，
             否则一条错误命令会杀掉整个 REPL。
    """

    code: int = ERR_USAGE

    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code
        self.data: dict[str, Any] = data or {}


class UsageError(CliError):
    """@brief 参数/用法错误（Agent 应改命令重试）。"""

    code = ERR_USAGE


class StateError(CliError):
    """@brief 会话状态不满足（例如未执行 project open）。"""

    code = ERR_STATE


class IoError(CliError):
    """@brief 文件/目录 IO 错误。"""

    code = ERR_IO


class ParseError(CliError):
    """@brief 数据内容解析错误。"""

    code = ERR_PARSE


class NativeError(CliError):
    """@brief 原生 MotionGloveSDK 库不可用。"""

    code = ERR_NATIVE


class UdpError(CliError):
    """@brief UDP 监听/取帧错误。"""

    code = ERR_UDP


class ExportError(CliError):
    """@brief 导出格式或目标不支持。"""

    code = ERR_EXPORT


@dataclass
class Envelope:
    """@brief 统一 JSON 信封。"""

    ok: bool
    code: int
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(
        cls, data: dict[str, Any] | None = None, message: str = "OK"
    ) -> "Envelope":
        """@brief 构造成功信封。"""
        return cls(True, OK, message, data or {})

    @classmethod
    def failure(
        cls,
        code: int,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> "Envelope":
        """@brief 构造失败信封。"""
        return cls(False, code, message, data or {})

    def to_dict(self) -> dict[str, Any]:
        """@brief 转为可 JSON 序列化的字典（data 永远存在）。"""
        return {
            "ok": bool(self.ok),
            "code": int(self.code),
            "message": str(self.message),
            "data": self.data if isinstance(self.data, dict) else {},
        }

    def render(self, as_json: bool) -> str:
        """@brief 渲染为一行 JSON 或人类可读文本。

        @param as_json True 输出机器可读 JSON；False 输出人类可读文本。
        @return 待打印的字符串（末尾不含换行）。
        """
        if as_json:
            return json.dumps(self.to_dict(), ensure_ascii=False)
        head = "[OK] " if self.ok else "[FAIL] "
        lines: list[str] = [
            f"{head}{self.message}",
            f"code: {self.code} ({ERROR_CODES.get(self.code, '未知')})",
        ]
        if self.data:
            lines.append("data:")
            lines.append(json.dumps(self.data, ensure_ascii=False, indent=2))
        return "\n".join(lines)

    @property
    def exit_code(self) -> int:
        """@brief 进程退出码：成功 0，失败 1。"""
        return 0 if self.ok else 1


def from_envelope_dict(obj: Any) -> "Envelope":
    """@brief 从外部 JSON 对象还原信封（harness 与 REPL 自检用）。

    @param obj 任意对象；必须是含 ok/code/message/data 的字典。
    @return Envelope 实例。
    @exception ValueError 结构不合法。
    """
    if not isinstance(obj, dict):
        raise ValueError("信封必须是 JSON 对象")
    missing = {"ok", "code", "message", "data"} - set(obj)
    if missing:
        raise ValueError(f"信封缺少字段：{sorted(missing)}")
    if not isinstance(obj["ok"], bool) or not isinstance(obj["code"], int):
        raise ValueError("信封字段类型错误：ok 必须为 bool，code 必须为 int")
    if not isinstance(obj["message"], str) or not isinstance(obj["data"], dict):
        raise ValueError("信封字段类型错误：message 必须为 str，data 必须为 object")
    return Envelope(obj["ok"], obj["code"], obj["message"], obj["data"])
