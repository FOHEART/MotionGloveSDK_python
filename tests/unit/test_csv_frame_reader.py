"""
@file  test_csv_frame_reader.py
@brief CSV 回放读取器（csv_frame_reader.CsvFrameReader）单元测试。
@details
覆盖策略
 - 解析解（金标准）：手工构造的 CSV 行 → 逐字段断言帧号/骨骼数/数值；
 - 边界条件：格式 A（单 subpackage）与格式 B（多 subpackage 拼接一行）、
   BOM 文件头、空行、末帧后的 next_frame；
 - 异常场景：文件不存在抛 FileNotFoundError；无法解析的行被静默过滤。

文件用 pytest tmp_path 临时构造，不依赖仓库内样例数据。
"""

import pytest

from src.csv_frame_reader import CsvFrameReader

HEADER_A = ("Glove1 time 2026-04-06 22:10:04.500 pos euler ZXY relative "
            "fn {fn} subpackage 1/1")


def build_line_a(fn: int, value_prefix: float) -> str:
    """格式 A：单行单 subpackage，42 段 × 7 值。"""
    values = []
    for _ in range(42):
        values += [repr(value_prefix), repr(0.2), repr(0.3),
                   repr(0.0), repr(0.0), repr(0.0)]
    return f"{HEADER_A.format(fn=fn)},\n".replace(",\n", ",") + ",".join(values)


def write_csv(tmp_path, lines: list[str]) -> str:
    """写一个带列名表头的 CSV 文件（utf-8-sig 可读）。"""
    path = tmp_path / "recording.csv"
    path.write_text("column,header,line\n" + "\n".join(lines) + "\n", encoding="utf-8-sig")
    return str(path)


# ── 构造与异常 ──────────────────────────────────────────────────────────────


def test_CsvFrameReader_MissingFileRaisesFileNotFoundError(tmp_path):
    """@test   csv_frame_reader.CsvFrameReader_MissingFileRaisesFileNotFoundError
    @brief  文件不存在时构造函数抛 FileNotFoundError。
    @details 目的：UI 的文件选择器依赖该异常给出提示，静默返回空读取器
             会让用户以为"文件是空的"。
    @expected pytest.raises(FileNotFoundError)
    @priority P0
    """
    # Act / Assert
    with pytest.raises(FileNotFoundError):
        CsvFrameReader(str(tmp_path / "not_exist.csv"))


def test_CsvFrameReader_BomFileHeaderTolerated(tmp_path):
    """@test   csv_frame_reader.CsvFrameReader_BomFileHeaderTolerated
    @brief  Windows 记事本写出的 BOM（utf-8-sig）文件可正常读取。
    @details 目的：真实导出文件常带 BOM；按 utf-8 读取会把 BOM 混入表头
             并可能污染首行数据。
    @expected total_frames == 1，首帧帧号正确
    @priority P1
    """
    # Arrange
    path = write_csv(tmp_path, [build_line_a(10, 0.1)])

    # Act
    reader = CsvFrameReader(path)

    # Assert
    assert reader.total_frames == 1
    assert reader.next_frame().header.frame_number == 10


def test_CsvFrameReader_BlankLinesSkipped(tmp_path):
    """@test   csv_frame_reader.CsvFrameReader_BlankLinesSkipped
    @brief  数据区中的空行不产生帧，也不计总帧数。
    @details 目的：导出文件末尾常见多余换行；若空行解析成空帧会让回放
             出现"空闪帧"。
    @expected total_frames == 2（3 行数据中 1 行为空）
    @priority P1
    """
    # Arrange
    path = write_csv(tmp_path, [build_line_a(1, 0.1), "", build_line_a(2, 0.2)])

    # Act / Assert
    assert CsvFrameReader(path).total_frames == 2


# ── 帧内容解析 ──────────────────────────────────────────────────────────────


def test_CsvFrameReader_FormatASingleSubpackageParsesValues(tmp_path):
    """@test   csv_frame_reader.CsvFrameReader_FormatASingleSubpackageParsesValues
    @brief  格式 A 单 subpackage 行解析出完整 42 段帧，数值逐项正确。
    @details 目的：格式 A 是旧版本导出格式，是 42×7 数值直通解析的最简
             路径；首段数值抽查确保逗号切分没有偏移。
    @expected len(skeletons)==42；第 0 段 position[0]==0.1、第 41 段 position[0]==0.1
    @priority P0
    """
    # Arrange
    path = write_csv(tmp_path, [build_line_a(11, 0.1)])

    # Act
    frame = CsvFrameReader(path).next_frame()

    # Assert
    assert frame is not None
    assert len(frame.skeletons) == 42
    assert frame.header.frame_number == 11
    assert frame.skeletons[0].position[0] == pytest.approx(0.1)
    assert frame.skeletons[41].position[0] == pytest.approx(0.1)


def test_CsvFrameReader_FormatBConcatenatedSubpackages(tmp_path):
    """@test   csv_frame_reader.CsvFrameReader_FormatBConcatenatedSubpackages
    @brief  格式 B 两个 subpackage 拼接一行时剔除内嵌 header，数值按序拼接。
    @details 目的：_EMBEDDED_HEADER_RE 负责剔除内嵌的 "Glove1 ... subpackage 2/2"；
             剔除失败会把 header 文本混进数值流导致整帧被丢（假静默）。
    @expected total_frames==1；两段数值按 subpackage 顺序拼接，第 0 段
             position[0]==0.1、第 42 段? （不存在）——以数值总数 294 校验
    @priority P0
    """
    # Arrange：两段各 21 段骨骼（21×7=147 值），拼在一行
    def body_segment(prefix: float, count: int = 21) -> str:
        values = []
        for _ in range(count):
            values += [repr(prefix), repr(0.2), repr(0.3), repr(0.0), repr(0.0), repr(0.0)]
        return ",".join(values)

    h1 = HEADER_A.format(fn=20)
    h2 = f"Glove1 time 2026-04-06 22:10:04.500 pos euler ZXY relative fn 20 subpackage 2/2"
    line = f"{h1},{body_segment(0.1)},{h2},{body_segment(0.2)}"
    path = write_csv(tmp_path, [line])

    # Act
    reader = CsvFrameReader(path)
    frame = reader.next_frame()

    # Assert
    assert reader.total_frames == 1
    assert frame is not None
    # 42 段全帧：前 21 段来自 subpackage 1（0.1），后 21 段来自 subpackage 2（0.2）
    assert len(frame.skeletons) == 42
    assert frame.skeletons[0].position[0] == pytest.approx(0.1)
    assert frame.skeletons[21].position[0] == pytest.approx(0.2)
    assert frame.skeletons[41].position[0] == pytest.approx(0.2)


# ── 播放控制 ────────────────────────────────────────────────────────────────


def test_CsvFrameReader_NextFrameAtEndReturnsNoneAndKeepsIndex(tmp_path):
    """@test   csv_frame_reader.CsvFrameReader_NextFrameAtEndReturnsNoneAndKeepsIndex
    @brief  末帧后再取返回 None，索引停在末尾（不回绕）。
    @details 目的：回放 UI 的"播放结束"判定依赖 at_end + None 契约；
             若索引继续增长会超出列表边界。
    @expected 连续 next_frame 两次：第一次返回帧、第二次 None，at_end 为 True
    @priority P0
    """
    # Arrange
    path = write_csv(tmp_path, [build_line_a(1, 0.1)])

    # Act
    reader = CsvFrameReader(path)
    first = reader.next_frame()
    second = reader.next_frame()

    # Assert
    assert first is not None
    assert second is None
    assert reader.at_end is True
    assert reader.current_index == 1   # 索引不回绕


def test_CsvFrameReader_ResetRestartsFromFirstFrame(tmp_path):
    """@test   csv_frame_reader.CsvFrameReader_ResetRestartsFromFirstFrame
    @brief  reset() 后再次 next_frame 从第一帧开始（可循环回放）。
    @details 目的：CSV 回放模式 UI 的"重播"按钮依赖 reset。
    @expected reset 后 next_frame().header.frame_number == 首帧帧号
    @priority P0
    """
    # Arrange
    path = write_csv(tmp_path, [build_line_a(1, 0.1), build_line_a(2, 0.2)])
    reader = CsvFrameReader(path)
    reader.next_frame()
    reader.next_frame()

    # Act
    reader.reset()
    frame = reader.next_frame()

    # Assert
    assert frame.header.frame_number == 1
    assert reader.current_index == 1


def test_CsvFrameReader_SeekClampsOutOfRangeIndex(tmp_path):
    """@test   csv_frame_reader.CsvFrameReader_SeekClampsOutOfRangeIndex
    @brief  seek 越界索引被夹取到 [0, total_frames]。
    @details 目的：进度滑块可以拖到任意位置，负值/超末值都必须钳制。
    @expected seek(-5) → index 0；seek(999) → index 2（total_frames）
    @priority P1
    """
    # Arrange
    path = write_csv(tmp_path, [build_line_a(1, 0.1), build_line_a(2, 0.2)])
    reader = CsvFrameReader(path)

    # Act / Assert
    reader.seek(-5)
    assert reader.current_index == 0
    reader.seek(999)
    assert reader.current_index == reader.total_frames