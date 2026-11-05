"""
@file  parser.py
@brief CLI 公共解析工具：BOM 剥离、引号感知 token 化、手写选项解析。
@details
不使用 argparse 的 parse_args()（它出错会 SystemExit 杀掉 REPL），
全部改为手动校验并抛 UsageError，由分发器转成统一信封。
"""

from __future__ import annotations

import sys
from typing import Any

from .envelope import UsageError

# 选项类型：value=单值，multi=可重复，flag=布尔开关
OptionSpec = dict[str, str]


def strip_bom(text: str) -> str:
    """@brief 剥离 UTF-8 BOM（脚本管道输入常带 BOM，否则首条命令识别失败）。

    @param text 原始文本。
    @return 去除 U+FEFF 后的文本。
    """
    return text.lstrip("\ufeff") if text.startswith("\ufeff") else text


def tokenize(line: str) -> list[str]:
    """@brief 把一行命令切成 token，支持成对单/双引号与含空格路径。

    @details Windows 下反斜杠按路径分隔符保留（不当转义符）；POSIX 下
             反斜杠转义下一个字符。引号本身不保留在 token 中。
    @param line 一行命令文本（可带 BOM）。
    @return token 列表。
    @exception UsageError 引号未闭合。
    """
    text = strip_bom(line)
    out: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    i = 0
    while i < len(text):
        ch = text[i]
        if quote is not None:
            if ch == quote:
                quote = None
            elif ch == "\\" and sys.platform != "win32" and i + 1 < len(text):
                i += 1
                buf.append(text[i])
            else:
                buf.append(ch)
        elif ch in ("'", '"'):
            quote = ch
        elif ch.isspace():
            if buf:
                out.append("".join(buf))
                buf = []
        elif ch == "\\" and sys.platform != "win32" and i + 1 < len(text):
            i += 1
            buf.append(text[i])
        else:
            buf.append(ch)
        i += 1

    if quote is not None:
        raise UsageError("引号未闭合，请检查命令中的单/双引号是否成对")
    if buf:
        out.append("".join(buf))
    return out


class Args:
    """@brief 解析结果容器。

    @details values 存放 multi 选项的所有值；opts 存放单值；
             flags 存放布尔开关；positional 存放位置参数。
    """

    def __init__(self) -> None:
        self.opts: dict[str, str] = {}
        self.values: dict[str, list[str]] = {}
        self.flags: set[str] = set()
        self.positional: list[str] = []

    def get(self, name: str, default: str | None = None) -> str | None:
        """@brief 取单值选项。"""
        return self.opts.get(name, default)

    def multi(self, name: str) -> list[str]:
        """@brief 取可重复选项的全部值。"""
        return list(self.values.get(name, []))

    def flag(self, name: str, default: bool = False) -> bool:
        """@brief 取布尔开关。"""
        return name in self.flags or default

    def to_payload(self, mapping: dict[str, str] | None = None) -> dict[str, Any]:
        """@brief 把已解析选项转成命令 payload 字典。

        @param mapping 选项名 → payload 键名的映射；未列出的选项用去掉
                       前导 "--" 并把 "-" 换成 "_" 的键名。
        @return payload 字典（不含值为 None 的项）。
        """
        mapping = mapping or {}
        payload: dict[str, Any] = {}
        for key, value in self.opts.items():
            payload[mapping.get(key, _key(key))] = value
        for key, values in self.values.items():
            payload[mapping.get(key, _key(key))] = list(values)
        for key in self.flags:
            payload[mapping.get(key, _key(key))] = True
        return payload


def _key(option: str) -> str:
    return option.lstrip("-").replace("-", "_")


def parse_tokens(tokens: list[str], spec: OptionSpec) -> Args:
    """@brief 解析 token 列表为 Args（出错抛 UsageError，不退出进程）。

    @details 支持 --key value、--key=value、可重复选项、布尔开关、位置参数，
             以及 "--" 之后全部按位置参数处理。未知选项一律报 ERR_USAGE。
    @param tokens 已 token 化的参数列表（不含程序名/命令名）。
    @param spec   允许的选项及其类型 {"--file": "value", ...}。
    @return Args 实例。
    @exception UsageError 未知选项、缺值、重复单值选项。
    """
    args = Args()
    i = 0
    positional_only = False
    while i < len(tokens):
        tok = tokens[i]
        if positional_only or not tok.startswith("--"):
            args.positional.append(tok)
            i += 1
            continue
        if tok == "--":
            positional_only = True
            i += 1
            continue

        name, sep, inline = tok.partition("=")
        kind = spec.get(name)
        if kind is None:
            raise UsageError(
                f"未知选项：{name}；可用选项：{', '.join(sorted(spec)) or '（无）'}"
            )

        if kind == "flag":
            if sep:
                raise UsageError(f"布尔选项 {name} 不接受取值：--{name}={inline}")
            args.flags.add(name)
            i += 1
            continue

        if sep:
            value = inline
        else:
            if i + 1 >= len(tokens) or tokens[i + 1].startswith("--"):
                raise UsageError(f"选项 {name} 缺少取值")
            value = tokens[i + 1]
            i += 1

        if kind == "multi":
            args.values.setdefault(name, []).append(value)
        else:
            if name in args.opts:
                raise UsageError(f"选项 {name} 不可重复指定")
            args.opts[name] = value
        i += 1
    return args


def as_int(
    value: Any,
    default: int,
    *,
    name: str,
    lo: int | None = None,
    hi: int | None = None,
) -> int:
    """@brief 把 payload 值转成 int 并做范围校验。

    @param value 待转换值；None 时返回 default。
    @param default 缺省值。
    @param name 字段名（错误信息用）。
    @param lo 最小值（含），None 表示不限。
    @param hi 最大值（含），None 表示不限。
    @return 合法整数。
    @exception UsageError 非整数或越界。
    """
    if value is None or value == "":
        return default
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise UsageError(f"{name} 必须是整数，当前值：{value!r}") from None
    if lo is not None and result < lo:
        raise UsageError(f"{name} 不能小于 {lo}，当前值：{result}")
    if hi is not None and result > hi:
        raise UsageError(f"{name} 不能大于 {hi}，当前值：{result}")
    return result


def as_float(
    value: Any,
    default: float,
    *,
    name: str,
    lo: float | None = None,
    hi: float | None = None,
) -> float:
    """@brief 把 payload 值转成 float 并做范围校验。

    @param value 待转换值；None 时返回 default。
    @param default 缺省值。
    @param name 字段名（错误信息用）。
    @param lo 最小值（含），None 表示不限。
    @param hi 最大值（含），None 表示不限。
    @return 合法浮点数。
    @exception UsageError 非数值或越界。
    """
    if value is None or value == "":
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise UsageError(f"{name} 必须是数值，当前值：{value!r}") from None
    if result != result or result in (float("inf"), float("-inf")):
        raise UsageError(f"{name} 必须是有限数值，当前值：{value!r}")
    if lo is not None and result < lo:
        raise UsageError(f"{name} 不能小于 {lo}，当前值：{result}")
    if hi is not None and result > hi:
        raise UsageError(f"{name} 不能大于 {hi}，当前值：{result}")
    return result


def as_bool(value: Any, default: bool = False) -> bool:
    """@brief 把 payload 值转成 bool（兼容 JSON bool 与 "1"/"true"/"yes" 字符串）。

    @param value 待转换值。
    @param default 值为 None 时的缺省。
    @return 布尔值。
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in ("1", "true", "yes", "on")


HELP_TEXT = """MotionGlove3DViewer CLI — 命令一览（所有命令均支持 --json）

  status                              查询后端/原生库/会话状态
  project open <path> [--actor A]     打开 CSV 工程并写入会话
  project open --udp [--port N]       切换到 UDP 数据源
  project new <path> [--frames N]     新建 CSV 工程（可生成 T-pose 示例帧）
  project close                       关闭当前工程
  project status                      查看当前会话
  run frame [--index N] [--summary]   取一帧（CSV 按索引 / UDP 等待一帧）
  run frames [--start N] [--count N]  连续取帧（默认输出摘要）
  run listen [--port N] [--seconds S] UDP 采集若干秒
  run bones                           查询 42/32 骨骼索引映射
  run port-check [--port N]           诊断 UDP 端口占用
  export <output> [--format F]        导出 json / csv / bvh（省略格式按扩展名推断）
                   [--input P] [--index N] [--count N] [--frame-rate HZ]

  所有命令也可用机器调用协议：--json <action> '<payload-json>'
  action: status / project.open / project.new / project.close / project.status /
          run.frame / run.frames / run.listen / run.bones / run.port-check / export

REPL: json on | json off | help | exit | quit（EOF 亦退出）
"""
