"""
Glove Frame Assembler - MotionGloveSDK Python
分包拼接 + 完整帧统计

功能：
  - 解析每个 UDP 包的文本内容，提取 actor 名称、fn（帧序号）、subpackage（x/y）
  - 按 fn 将属于同一帧的分包拼接为完整帧的 CSV 数据部分
  - 统计实际收到的完整帧数

对应 C++ 实现：
  MotionGloveSDK/src/decodeAsGloveCSV.cpp - GloveSplitFrameMgr

调用方式：
  from glove_frame_assembler import GloveFrameAssembler

  def on_frame(actor, fn, body_csv, header_tokens):
      print(actor, fn)

  assembler = GloveFrameAssembler(on_complete_frame=on_frame)
  assembler.feed(raw_text)  # 每收到一个 UDP 包调用一次
"""

from typing import Callable


class _SubpackageState:
    """
    单个 actor 当前正在拼接的帧的状态。
    对应 C++ GloveSplitFrameMgr 的各成员字段。
    """
    __slots__ = ("fn", "sub_max", "received", "body_parts", "header_tokens")

    def __init__(self):
        self.reset()

    def reset(self):
        self.fn: int = -1
        self.sub_max: int = 0
        self.received: set = set()       # 已收到的分包编号（1-based）
        self.body_parts: dict = {}       # {sub_index: body_str}
        self.header_tokens: list = []    # 第一个分包的 header tokens


class GloveFrameAssembler:
    """
    CSV 分包拼接器。

    每次收到一个 UDP 包的文本内容，调用 feed()。
    当某个 fn 的所有分包都收齐后，调用 on_complete_frame 回调。

    对应 C++ GloveSplitFrameMgr + decodeAsGloveCSV_Func() 中的分包处理逻辑。
    """

    def __init__(self, on_complete_frame: Callable[[str, int, str, list], None]):
        """
        参数：
          on_complete_frame(actor_name, fn, body_csv, header_tokens)
            actor_name    : 演员名称，例如 "Glove1"
            fn            : 帧序号
            body_csv      : 拼接完成的 CSV 数据部分（不含 header 行）
            header_tokens : header 行按空格分割后的 token 列表（供 decode_glove_csv 使用）
        """
        self._on_complete = on_complete_frame
        self._states: dict[str, _SubpackageState] = {}

        self.complete_frame_count: int = 0   # 已拼接完成的完整帧总数

    def feed(self, raw_text: str) -> bool:
        """
        喂入一个 UDP 包的文本内容，尝试拼接分包。

        返回 True  : 包含 subpackage 字段，已成功处理
        返回 False : 格式不符（非手套 CSV 包），跳过

        对应 C++ decodeAsGloveCSV_Func() 中的 header 解析 + 分包重组逻辑。
        """
        # ------------------------------------------------------------------
        # 1. 分离 header 与 body
        #    格式：<header tokens 以空格分隔>,<csv 数值>,...
        #    header 是第一个逗号之前的部分
        # ------------------------------------------------------------------
        comma_idx = raw_text.find(",")
        if comma_idx == -1:
            return False

        header_str = raw_text[:comma_idx].strip()
        body_str = raw_text[comma_idx + 1:]

        tokens = header_str.split()
        if not tokens:
            return False

        actor_name = tokens[0]

        # ------------------------------------------------------------------
        # 2. 提取 fn（帧序号）
        #    header 中含 "fn <number>"
        # ------------------------------------------------------------------
        try:
            fn_idx = tokens.index("fn")
            fn = int(tokens[fn_idx + 1])
        except (ValueError, IndexError):
            return False

        # ------------------------------------------------------------------
        # 3. 提取 subpackage x/y
        #    header 中含 "subpackage <x>/<y>"
        #    对应 C++ 中 splitHeaderVec 查找 "subpackage" token
        # ------------------------------------------------------------------
        try:
            sp_idx = tokens.index("subpackage")
            sp_cur, sp_max = tokens[sp_idx + 1].split("/")
            sub_cur = int(sp_cur)
            sub_max = int(sp_max)
        except (ValueError, IndexError):
            return False

        # ------------------------------------------------------------------
        # 4. 获取或初始化该 actor 的拼接状态
        #    对应 C++ m_GloveSplitFrameMgr.fn != sh->frameNumber 的分支判断
        # ------------------------------------------------------------------
        if actor_name not in self._states:
            self._states[actor_name] = _SubpackageState()

        state = self._states[actor_name]

        if state.fn != fn:
            # 新帧，重置状态；保存 header tokens（同一帧各分包 header 相同，只存一次）
            state.reset()
            state.fn            = fn
            state.sub_max       = sub_max
            state.header_tokens = tokens

        # ------------------------------------------------------------------
        # 5. 存入当前分包
        # ------------------------------------------------------------------
        state.received.add(sub_cur)
        state.body_parts[sub_cur] = body_str

        # ------------------------------------------------------------------
        # 6. 检查是否集齐所有分包
        #    对应 C++ checkFrameComplete()：subFrameVec.size() == subFrameMax
        # ------------------------------------------------------------------
        if len(state.received) == state.sub_max:
            full_body = "".join(state.body_parts[i] for i in range(1, state.sub_max + 1))
            self.complete_frame_count += 1
            self._on_complete(actor_name, fn, full_body, state.header_tokens)
            state.reset()

        return True
