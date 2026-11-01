"""
@file  test_config_io.py
@brief config_io 读写配置单元测试。
@details
覆盖策略
 - 不变量：写后读 roundtrip 一致；写后不残留 .tmp 临时文件（原子替换语义）；
 - 边界条件：空字典、含中文键值的非 ASCII 配置（ensure_ascii=False）；
 - 异常场景：配置文件不存在 / JSON 损坏 / JSON 为 null 时 read_config()
   返回空字典且不抛异常——上层不应因配置问题崩溃。

通过 monkeypatch 替换模块级 CONFIG_PATH，使测试写入 tmp_path 而不污染
项目根目录的真实 config.json。
"""

import json

import pytest

from src import config_io


@pytest.fixture()
def config_path(tmp_path, monkeypatch):
    """把 CONFIG_PATH 指向临时目录，返回其绝对路径。"""
    path = tmp_path / "config.json"
    monkeypatch.setattr(config_io, "CONFIG_PATH", str(path))
    return path


# ── 正常读写 ────────────────────────────────────────────────────────────────


def test_ConfigIO_WriteThenReadRoundtrip(config_path):
    """@test   config_io.WriteThenReadRoundtrip
    @brief  write_config 写入后 read_config 能读回相同内容。
    @details 目的：配置持久化的最基本契约——写什么读什么。
    @expected roundtrip 后内容与原 dict 相等（== 而非 is，键序无关）
    @priority P0
    """
    # Arrange
    cfg = {"listen_port": 5001, "actors": ["Glove1", "Glove2"], "verbose": True}

    # Act
    config_io.write_config(cfg)
    loaded = config_io.read_config()

    # Assert
    assert loaded == cfg


def test_ConfigIO_RoundtripPreservesNonAscii(config_path):
    """@test   config_io.RoundtripPreservesNonAscii
    @brief  中文键值经 write/read roundtrip 后不乱码。
    @details 目的：write_config 用 ensure_ascii=False 落盘，中文应原样
             存为 UTF-8 而非 \\uXXXX 转义（便于人工排查配置文件）。
    @expected 读回内容与原值相等，且文件原始文本包含中文而非转义序列
    @priority P1
    """
    # Arrange
    cfg = {"数据流": "Glove1", "备注": "左手套"}

    # Act
    config_io.write_config(cfg)
    loaded = config_io.read_config()

    # Assert
    assert loaded == cfg
    assert "左手套" in config_path.read_text(encoding="utf-8")


def test_ConfigIO_NoTmpFileResidueAfterWrite(config_path):
    """@test   config_io.NoTmpFileResidueAfterWrite
    @brief  write_config 完成后 .tmp 临时文件被原子替换掉、不残留。
    @details 目的：写入流程为 临时文件 + os.replace 原子替换；若残留
             .tmp 会误导用户以为是写坏了一半的配置。
    @expected CONFIG_PATH 存在、CONFIG_PATH + ".tmp" 不存在
    @priority P0
    """
    # Act
    config_io.write_config({"a": 1})

    # Assert
    assert config_path.exists()
    import os

    assert not os.path.exists(str(config_path) + ".tmp")


# ── 异常输入 ────────────────────────────────────────────────────────────────


def test_ConfigIO_MissingFileReturnsEmptyDict(config_path):
    """@test   config_io.MissingFileReturnsEmptyDict
    @brief  配置文件不存在时 read_config 返回空字典（首次运行场景）。
    @details 目的：项目根目录还没有 config.json 是常见初始状态，
             不应抛 FileNotFoundError。
    @expected 返回值 == {}
    @priority P0
    """
    # Act / Assert
    assert config_io.read_config() == {}


def test_ConfigIO_CorruptJsonReturnsEmptyDict(config_path):
    """@test   config_io.CorruptJsonReturnsEmptyDict
    @brief  JSON 损坏（非法语法）时 read_config 返回空字典且不抛异常。
    @details 目的：用户手改配置写坏 JSON 是高频事故；宁可回退默认
             空配置，也不能让 SDK 启动崩溃。
    @expected 返回值 == {}
    @priority P0
    """
    # Arrange：写入非法 JSON
    config_path.write_text("{ this is not json", encoding="utf-8")

    # Act / Assert
    assert config_io.read_config() == {}


def test_ConfigIO_NullJsonReturnsEmptyDict(config_path):
    """@test   config_io.NullJsonReturnsEmptyDict
    @brief  JSON 内容为字面量 null 时 read_config 返回空字典。
    @details 目的：json.load 会把 "null" 解析成 None，read_config 内部
             用 `or {}` 把 None 归一为空字典——锁定该边界行为。
    @expected 返回值 == {}（而非 None）
    @priority P2
    """
    # Arrange
    config_path.write_text(json.dumps(None), encoding="utf-8")

    # Act / Assert
    assert config_io.read_config() == {}
