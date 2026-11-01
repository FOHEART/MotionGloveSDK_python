"""
@file  csv_frame_reader.py
@brief 从 MotionGlove CSV 导出文件逐帧读取骨骼数据。
@details
文件格式（两种）：
  第 1 行：列名表头（跳过）
  第 2 行起每行代表一帧，支持两种 subpackage 格式：

  格式 A（每行单 subpackage，旧版本）：
      <header tokens（空格分隔）>,<骨骼数据（逗号分隔）>
      示例：
          Glove1 time 2026-04-06 22:10:04 pos euler ZXY relative fn 496 subpackage 1/1,0.1,0,...

  格式 B（每行含多个 subpackage 拼接，新版本）：
      <header1>,<数值1...>,<header2>,<数值2...>
      示例：
          Glove1 ... subpackage 1/2,<数值>,Glove1 ... subpackage 2/2,<数值>

公开接口（类 CsvFrameReader）：
  - 构造时将全部数据行预解析为 GloveFrame 列表存入内存；
  - next_frame() 顺序取帧，末帧后返回 None；
  - reset() / seek() 控制读取位置；
  - 属性 total_frames / current_index / at_end。

文件以 utf-8-sig 打开，兼容带 BOM 的导出文件。
测试：tests/unit/test_csv_frame_reader.py。
"""

from __future__ import annotations

import re
from pathlib import Path

from .decode_glove_csv import decode_glove_csv
from .definitions import GloveFrame


# 匹配嵌入在数值流中的第二段（及后续段）header。
# header 的特征：以 avatar 名（无逗号的单词）开头，包含 "subpackage N/M" 结尾。
# 模式：,<word> <word> ... subpackage N/M  后面紧跟逗号或行尾
_EMBEDDED_HEADER_RE = re.compile(
    r',([^,]+? subpackage \d+/\d+)(?=,|$)'
)


class CsvFrameReader:
    """@brief 预加载 MotionGlove CSV 导出文件，按行顺序提供 GloveFrame。

    @details 构造即完成全文件解析（一次性 I/O），之后 next_frame() 为
             纯内存操作，适合回放循环。解析失败的行（返回 None）被
             静默丢弃，不占用帧索引。
    """

    def __init__(self, path: str) -> None:
        """@brief 读取并预解析 CSV 文件。

        @param path CSV 文件路径（绝对或相对均可），以 utf-8-sig 打开。
        @return 无（None）。
        @exception FileNotFoundError 文件不存在时抛出。
        """
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"CSV 文件不存在：{path}")

        with open(p, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()

        # 跳过第一行（列名表头），预解析全部行为 GloveFrame 并过滤 None
        self._frames: list[GloveFrame] = []
        for line in lines[1:]:
            line = line.rstrip("\n\r")
            if not line.strip():
                continue
            frame = self._parse_line(line)
            if frame is not None:
                self._frames.append(frame)

        self._index: int = 0

    # ── 公开接口 ──────────────────────────────────

    @property
    def total_frames(self) -> int:
        """@brief 数据行总数（不含表头行）。@return 帧数，非负整数。"""
        return len(self._frames)

    @property
    def current_index(self) -> int:
        """@brief 当前读取索引。@return 0-based 索引，[0, total_frames]。"""
        return self._index

    @property
    def at_end(self) -> bool:
        """@brief 是否已到末尾。@return 当前索引超出帧数范围时为 True。"""
        return self._index >= len(self._frames)

    def reset(self) -> None:
        """@brief 将索引归零，下次 next_frame() 从第一帧开始。@return 无（None）。"""
        self._index = 0

    def seek(self, index: int) -> None:
        """@brief 将索引直接定位到指定帧，越界值夹紧到合法范围。

        @param index 目标索引（0-based）；负数按 0 处理，超过帧数按末尾处理。
        @return 无（None）。
        """
        self._index = max(0, min(index, len(self._frames)))

    def next_frame(self) -> GloveFrame | None:
        """@brief 返回当前索引对应的 GloveFrame 并将索引加 1。

        @return GloveFrame（正常）；已到末帧（at_end 为 True）→ None，
                且索引保持不变。
        """
        if self.at_end:
            return None
        frame = self._frames[self._index]
        self._index += 1
        return frame

    # ── 内部解析 ──────────────────────────────────

    @staticmethod
    def _parse_line(line: str) -> GloveFrame | None:
        """@brief 将 CSV 单行解析为 GloveFrame。

        支持格式 A（单 subpackage）和格式 B（多 subpackage 拼接在同一行）。
        多段 subpackage 的 header 会被剔除，所有数值段拼接后统一传给
        decode_glove_csv。

        @param line 去除行尾换行后的 CSV 数据行文本。
        @return GloveFrame（成功）；无逗号、header 为空或数值不合法 → None。
        """
        # 取第一段 header（到第一个逗号为止）
        comma_idx = line.find(',')
        if comma_idx == -1:
            return None

        header_str = line[:comma_idx]
        remainder  = line[comma_idx + 1:]   # 第一个逗号之后的全部内容

        tokens = header_str.split()
        if not tokens:
            return None

        actor = tokens[0]
        fn = 0
        if "fn" in tokens:
            try:
                fn_idx = tokens.index("fn")
                fn = int(tokens[fn_idx + 1])
            except (IndexError, ValueError):
                pass

        # 剔除 remainder 中所有嵌入的 subpackage header，保留纯数值
        # 格式 B 示例：<数值...>,Glove1 time ... subpackage 2/2,<数值...>
        # _EMBEDDED_HEADER_RE 匹配 ",<header文本>"，将其替换为 ","（保留数值间隔）
        body_csv = _EMBEDDED_HEADER_RE.sub(',', remainder)
        # 去掉可能产生的首尾多余逗号
        body_csv = body_csv.strip(',')

        return decode_glove_csv(actor, fn, body_csv, tokens)
