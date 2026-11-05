"""
@file  test_core.py
@brief harness 全 mock 单测：argv 映射 / 信封解析 / 错误路径 / REPL / Click 树。
@details 不启动底层 CLI，不依赖原生库、VTK、PySide6。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

_HARNESS_ROOT = Path(__file__).resolve().parents[3]
if str(_HARNESS_ROOT) not in sys.path:
    sys.path.insert(0, str(_HARNESS_ROOT))

from cli_anything.motionglove import _cli  # noqa: E402
from cli_anything.motionglove.utils import backend, repl_skin  # noqa: E402

ACTIONS = (
    "status", "project.open", "project.new", "project.close",
    "project.status", "run.frame", "run.frames", "run.listen",
    "run.bones", "run.port-check", "export",
)
PY_PREFIX = ["python", "motionGloveSDK_cli.py"]


class FakeProc:
    """@brief subprocess.run 返回对象的测试替身。"""

    def __init__(self, stdout: str, returncode: int = 0, stderr: str = "") -> None:
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


def _envelope(ok: bool = True, code: int = 0, message: str = "OK") -> str:
    return json.dumps({"ok": ok, "code": code, "message": message, "data": {}})


# ── build_argv（纯函数）──────────────────────────────────────────────────

@pytest.mark.parametrize("action", ACTIONS)
def test_build_argv_maps_every_action(action):
    """@expected argv = prefix + --json + action + payload-json，无 I/O。"""
    payload = {"path": "C:\\rec with space\\a.csv", "index": 2}
    argv = backend.build_argv(action, payload, PY_PREFIX)
    assert argv[:2] == PY_PREFIX
    assert argv[2] == "--json"
    assert argv[3] == action
    assert json.loads(argv[4]) == payload


def test_build_argv_gui_exe_adds_cli_flag():
    """@expected GUI 主程序前缀自动追加 --cli。"""
    prefix = backend.as_prefix("D:/dist/MotionGlove3DViewer.exe")
    assert prefix[-1] == "--cli"
    argv = backend.build_argv("status", {}, prefix)
    assert argv[2] == "--json" and argv[3] == "status"
    assert backend.needs_cli_flag("MotionGlove3DViewer.exe") is True
    assert backend.needs_cli_flag("MotionGloveCLI.exe") is False


def test_build_argv_rejects_bad_arguments():
    """@expected 空 action / 空前缀 / 非 dict payload 抛 ValueError。"""
    with pytest.raises(ValueError):
        backend.build_argv("", {}, PY_PREFIX)
    with pytest.raises(ValueError):
        backend.build_argv("status", {}, [])
    with pytest.raises(ValueError):
        backend.build_argv("status", ["not", "a", "dict"], PY_PREFIX)  # type: ignore[arg-type]


# ── 信封解析 ────────────────────────────────────────────────────────────

def test_parse_envelope_valid_and_tolerates_diagnostic_lines():
    """@expected 前置诊断行被忽略，取最后一条合法信封。"""
    out = "[MotionGloveSDK] init\n" + _envelope(message="状态查询成功")
    env = backend.parse_envelope(out)
    assert env["ok"] is True and env["code"] == 0
    assert env["message"] == "状态查询成功" and env["data"] == {}


def test_parse_envelope_bom_and_data():
    """@expected BOM 前缀被剥离，data 字段保留。"""
    env = backend.parse_envelope(
        "\ufeff" + json.dumps({"ok": True, "code": 0, "message": "m", "data": {"a": 1}})
    )
    assert env["data"] == {"a": 1}


@pytest.mark.parametrize("stdout", ["", "not json", '{"ok":true}',
                                     '{"ok":"yes","code":0,"message":"m","data":{}}'])
def test_parse_envelope_invalid_raises_protocol_error(stdout):
    """@expected 空输出/非 JSON/缺字段/类型错 → CliProtocolError。"""
    with pytest.raises(backend.CliProtocolError):
        backend.parse_envelope(stdout)


# ── invoke 错误分层 ──────────────────────────────────────────────────────

def test_invoke_returns_business_failure_envelope_verbatim():
    """@expected 业务失败信封原样返回，returncode=1，不抛异常。"""
    env, rc = backend.invoke(
        "project.open", {"path": "missing.csv"}, cli_prefix=PY_PREFIX,
        runner=lambda *a, **k: FakeProc(_envelope(False, 3, "CSV 文件不存在"), 1),
    )
    assert env["ok"] is False and env["code"] == 3
    assert rc == 1


def test_invoke_raises_cli_error_on_timeout():
    """@expected 超时映射为 CliError，不泄漏 TimeoutExpired。"""
    def _timeout(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="cli", timeout=1.0)

    with pytest.raises(backend.CliError, match="超时"):
        backend.invoke("status", {}, cli_prefix=PY_PREFIX, runner=_timeout)


def test_invoke_raises_cli_error_on_missing_binary():
    """@expected FileNotFoundError 映射为 CliError。"""
    def _missing(*_a, **_k):
        raise FileNotFoundError("no such file")

    with pytest.raises(backend.CliError, match="不存在"):
        backend.invoke("status", {}, cli_prefix=PY_PREFIX, runner=_missing)


def test_invoke_raises_cli_error_on_abnormal_exit_code():
    """@expected Windows 无符号大退出码被判为异常退出。"""
    with pytest.raises(backend.CliError, match="异常退出"):
        backend.invoke(
            "status", {}, cli_prefix=PY_PREFIX,
            runner=lambda *a, **k: FakeProc(_envelope(), 4294967294),
        )


# ── 二进制定位 ──────────────────────────────────────────────────────────

def test_resolve_cli_prefix_env_var_wins(monkeypatch, tmp_path):
    """@expected MOTIONGLOVE_CLI_BIN 优先于所有目录候选。"""
    exe = tmp_path / "MotionGloveCLI.exe"
    exe.write_text("", encoding="utf-8")
    monkeypatch.setenv(backend.ENV_CLI_BIN, str(exe))
    (tmp_path / backend.CLI_SCRIPT).write_text("", encoding="utf-8")
    assert backend.resolve_cli_prefix(probe=False, root=tmp_path)[0] == str(exe)


def test_resolve_cli_prefix_falls_back_to_python_entry(monkeypatch, tmp_path):
    """@expected 旧 exe 探测失败时跳过，回退源码 python 入口。"""
    monkeypatch.delenv(backend.ENV_CLI_BIN, raising=False)
    dist = tmp_path / "dist" / "MotionGlove3DViewer"
    dist.mkdir(parents=True)
    (dist / "MotionGlove3DViewer.exe").write_text("", encoding="utf-8")
    (tmp_path / backend.CLI_SCRIPT).write_text("", encoding="utf-8")
    monkeypatch.setattr(backend, "_probe", lambda _p: False)
    prefix = backend.resolve_cli_prefix(root=tmp_path)
    assert prefix[1].endswith(backend.CLI_SCRIPT)


def test_deployed_layout_locates_sibling_gui_exe(tmp_path):
    """@expected 安装目录里 exe 与 agent-harness 同级时自动定位并追加 --cli。"""
    exe = tmp_path / "MotionGlove3DViewer.exe"
    exe.write_text("", encoding="utf-8")
    (tmp_path / "SKILL.md").write_text("skill", encoding="utf-8")
    prefixes = backend.candidate_prefixes(root=tmp_path)
    assert prefixes[0] == [str(exe), "--cli"]
    assert (tmp_path / "SKILL.md").is_file()


def test_resolve_cli_prefix_no_candidate_raises(monkeypatch, tmp_path):
    """@expected 没有任何候选时给出可操作的 CliError。"""
    monkeypatch.delenv(backend.ENV_CLI_BIN, raising=False)
    monkeypatch.setattr(backend.shutil, "which", lambda _n: None)
    with pytest.raises(backend.CliError, match="未找到 CLI"):
        backend.resolve_cli_prefix(probe=False, root=tmp_path)


# ── REPL ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("line,kind,expected", [
    ("status", "command", ("status", {})),
    ("project open \"C:\\rec with space\\a.csv\"", "command",
     ("project.open", {"path": "C:\\rec with space\\a.csv"})),
    ("project new out.csv --frames 3", "command",
     ("project.new", {"path": "out.csv", "frames": "3"})),
    ("run frame --index 2 --summary", "command",
     ("run.frame", {"index": "2", "summary": True})),
    ("export out.json --format json --input in.csv", "command",
     ("export", {"output": "out.json", "format": "json", "input": "in.csv"})),
    ("run port-check --port 5001", "command",
     ("run.port-check", {"port": "5001"})),
    ("\ufeffstatus", "command", ("status", {})),
    ("exit", "exit", None),
    ("quit", "exit", None),
    ("json on", "json", True),
    ("json off", "json", False),
    ("help", "help", None),
    ("", "empty", None),
])
def test_repl_translate(line, kind, expected):
    """@expected 行翻译支持引号路径、BOM、选项映射与 REPL 内建指令。"""
    assert repl_skin.translate(line) == (kind, expected)


def test_repl_json_switch_really_changes_output():
    """@expected json on 输出原始信封 JSON，off 输出人类可读文本。"""
    calls: list[tuple[str, dict]] = []

    def _call(action, payload):
        calls.append((action, payload))
        return {"ok": True, "code": 0, "message": "m", "data": {"x": 1}}

    lines = iter(["json on", "status", "json off", "status", "exit"])
    printed: list[str] = []
    skin = repl_skin.ReplSkin(
        call=_call, reader=lambda _p: next(lines), printer=printed.append
    )
    assert skin.run() == 0
    raw_outputs = [s for s in printed if s.startswith('{"ok"')]
    human_outputs = [s for s in printed if s.startswith("[OK]")]
    assert len(raw_outputs) == 1 and json.loads(raw_outputs[0])["ok"] is True
    assert len(human_outputs) == 1 and "code: 0" in human_outputs[0]
    assert calls == [("status", {}), ("status", {})]


def test_repl_eof_exits_cleanly():
    """@expected EOF（Ctrl+D/Ctrl+Z）正常收尾，返回 0。"""
    def _eof(_p):
        raise EOFError

    printed: list[str] = []
    skin = repl_skin.ReplSkin(reader=_eof, printer=printed.append)
    assert skin.run() == 0


def test_repl_backend_error_is_printed_not_raised():
    """@expected 后端错误在 REPL 内转成文本，不杀掉 REPL。"""
    def _boom(_a, _p):
        raise backend.CliError("CLI 起不来")

    printed: list[str] = []
    lines = iter(["status", "exit"])
    skin = repl_skin.ReplSkin(
        call=_boom, reader=lambda _p: next(lines), printer=printed.append
    )
    assert skin.run() == 0
    assert any("CLI 起不来" in s for s in printed)


# ── Click 命令树 ────────────────────────────────────────────────────────

def test_click_tree_maps_subcommands_to_actions(monkeypatch):
    """@expected Click 子命令映射为 action+payload；失败信封 → 退出码 1。"""
    seen: list[tuple[str, dict]] = []

    def _fake_call(action, payload, **_kw):
        seen.append((action, payload))
        return {"ok": True, "code": 0, "message": "ok", "data": {"a": 1}}

    monkeypatch.setattr(_cli.backend, "call", _fake_call)
    runner = CliRunner()
    result = runner.invoke(_cli.main, ["--cli-bin", "dummy.exe", "project", "open", "a.csv"])
    assert result.exit_code == 0, result.output
    assert seen == [("project.open", {"path": "a.csv"})]

    result = runner.invoke(_cli.main, ["--cli-bin", "dummy.exe", "--raw", "run", "frame", "--index", "2"])
    assert result.exit_code == 0, result.output
    assert seen[-1] == ("run.frame", {"index": 2})
    assert '"ok": true' in result.output or '"ok":true' in result.output


def test_click_help_lists_command_groups():
    """@expected --help 列出 project / run / export / status / repl。"""
    result = CliRunner().invoke(_cli.main, ["--help"])
    assert result.exit_code == 0
    for name in ("project", "run", "export", "status", "repl"):
        assert name in result.output
