"""
@file  test_full_e2e.py
@brief 真调底层 CLI 的端到端测试（成功信封、错误码、退出码、导出文件、REPL）。
@details 找不到 CLI 入口时整组 skip，保证 CI 无构建产物时不误报失败。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_HARNESS_ROOT = Path(__file__).resolve().parents[3]
_APP_ROOT = _HARNESS_ROOT.parent
if str(_HARNESS_ROOT) not in sys.path:
    sys.path.insert(0, str(_HARNESS_ROOT))

from cli_anything.motionglove.utils import backend  # noqa: E402

CLI_ENTRY = _APP_ROOT / "motionGloveSDK_cli.py"
GUI_ENTRY = _APP_ROOT / "motionGloveSDK_example3_3dView.py"

pytestmark = pytest.mark.skipif(
    not CLI_ENTRY.is_file(),
    reason="未找到 motionGloveSDK_cli.py（无 CLI 入口，e2e 整组跳过）",
)

_HAS_GUI_DEPS = (
    any(
        (_APP_ROOT / "libs" / name).exists()
        for name in ("vtk", "vtk.py", "vtkmodules")
    )
    and (_APP_ROOT / "libs" / "PySide6").is_dir()
)


@pytest.fixture(scope="module")
def cli_prefix():
    """@brief 直接指定源码入口，绕开二进制定位（e2e 测的是协议本身）。"""
    return [sys.executable, str(CLI_ENTRY)]


@pytest.fixture
def project(tmp_path, cli_prefix):
    """@brief 每个用例独立新建 3 帧 CSV 工程，并在结束时关闭会话。"""
    backend.call("project.close", {}, cli_prefix=cli_prefix)
    csv_path = tmp_path / "rec.csv"
    env = backend.call(
        "project.new",
        {"path": str(csv_path), "frames": 3, "force": True},
        cli_prefix=cli_prefix,
    )
    assert env["ok"], env
    yield str(csv_path)
    backend.call("project.close", {}, cli_prefix=cli_prefix)


def _raw(argv: list[str], **kwargs) -> subprocess.CompletedProcess:
    """@brief 直接跑 CLI（不经 harness），用于非 --json / REPL / 非法 payload。"""
    return subprocess.run(
        [sys.executable, str(CLI_ENTRY), *argv],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60, **kwargs,
    )


def _envelope_from(proc: subprocess.CompletedProcess) -> dict:
    """@brief 从 stdout 取最后一行信封。"""
    return json.loads(proc.stdout.strip().splitlines()[-1])


# ── 成功路径 ────────────────────────────────────────────────────────────

def test_status_e2e_success_and_no_gui(cli_prefix):
    """@expected ok=true、code=0、gui_loaded=false、进程退出码 0。"""
    env, rc = backend.invoke("status", {}, cli_prefix=cli_prefix)
    assert env["ok"] is True and env["code"] == 0 and rc == 0
    assert env["data"]["gui_loaded"] is False
    assert env["data"]["app"] == "MotionGlove3DViewer"
    assert "project.open" in env["data"]["actions"]


def test_project_lifecycle_e2e(cli_prefix, project):
    """@expected open/status/close 会话跨进程可见。"""
    opened = backend.call("project.status", {}, cli_prefix=cli_prefix)
    assert opened["ok"] and opened["data"]["opened"] is True
    assert opened["data"]["total_frames"] == 3

    closed = backend.call("project.close", {}, cli_prefix=cli_prefix)
    assert closed["ok"] and closed["data"]["closed"] is True

    after = backend.call("project.status", {}, cli_prefix=cli_prefix)
    assert after["data"]["opened"] is False


def test_run_frame_e2e(cli_prefix, project):
    """@expected CSV 取帧返回 42 骨骼完整帧数据。"""
    env = backend.call("run.frame", {"index": 1}, cli_prefix=cli_prefix)
    assert env["ok"] and env["code"] == 0
    assert env["data"]["bone_count"] == 42
    assert env["data"]["frame_number"] == 2
    assert env["data"]["frame"]["header"]["frame_number"] == 2
    assert len(env["data"]["frame"]["skeletons"]) == 42


def test_run_frames_and_bones_e2e(cli_prefix, project):
    """@expected 批量取帧摘要与骨骼映射表可用。"""
    many = backend.call("run.frames", {"count": 2}, cli_prefix=cli_prefix)
    assert many["ok"] and many["data"]["returned"] == 2
    assert len(many["data"]["frames"]) == 2

    bones = backend.call("run.bones", {}, cli_prefix=cli_prefix)
    assert bones["ok"] and len(bones["data"]["bone_names"]) == 42
    assert len(bones["data"]["map_32_to_42"]) == 32


def test_export_all_formats_e2e(cli_prefix, project, tmp_path):
    """@expected json/csv/bvh 三个文件真实生成且内容可解析。"""
    out_json = tmp_path / "frames.json"
    out_csv = tmp_path / "frames.csv"
    out_bvh = tmp_path / "frames.bvh"

    for out in (out_json, out_csv, out_bvh):
        env, rc = backend.invoke(
            "export", {"output": str(out)}, cli_prefix=cli_prefix
        )
        assert env["ok"], env
        assert rc == 0 and out.is_file() and out.stat().st_size > 0
        assert env["data"]["frames"] == 3

    body = json.loads(out_json.read_text(encoding="utf-8"))
    assert len(body["frames"]) == 3
    assert out_csv.read_text(encoding="utf-8").splitlines()[0] == "column,header,line"
    assert "HIERARCHY" in out_bvh.read_text(encoding="utf-8")


def test_export_format_from_extension_e2e(cli_prefix, project, tmp_path):
    """@expected 省略 --format 时按扩展名推断。"""
    out = tmp_path / "inferred.csv"
    env = backend.call("export", {"output": str(out)}, cli_prefix=cli_prefix)
    assert env["ok"] and env["data"]["format"] == "csv" and out.is_file()


def test_export_roundtrip_csv_e2e(cli_prefix, project, tmp_path):
    """@expected 导出 CSV 可被 CsvFrameReader 再次读回（project open 成功）。"""
    out = tmp_path / "roundtrip.csv"
    assert backend.call("export", {"output": str(out)}, cli_prefix=cli_prefix)["ok"]
    env = backend.call("project.open", {"path": str(out)}, cli_prefix=cli_prefix)
    assert env["ok"] and env["data"]["total_frames"] == 3


# ── 错误路径 ────────────────────────────────────────────────────────────

def test_unknown_action_e2e(cli_prefix):
    """@expected 未知命令 code=1 且进程退出码 1。"""
    env, rc = backend.invoke("no.such.command", {}, cli_prefix=cli_prefix)
    assert env["ok"] is False and env["code"] == 1 and rc == 1


def test_missing_file_error_e2e(cli_prefix, tmp_path):
    """@expected 打开不存在的 CSV → code=3。"""
    env = backend.call(
        "project.open", {"path": str(tmp_path / "nope.csv")}, cli_prefix=cli_prefix
    )
    assert env["ok"] is False and env["code"] == 3


def test_no_project_state_error_e2e(cli_prefix):
    """@expected 未打开工程时 run.frame → code=2。"""
    backend.call("project.close", {}, cli_prefix=cli_prefix)
    env = backend.call("run.frame", {}, cli_prefix=cli_prefix)
    assert env["ok"] is False and env["code"] == 2


def test_missing_output_and_bad_dir_e2e(cli_prefix, tmp_path):
    """@expected 缺 output → code=1；输出目录不存在 → code=3。"""
    missing = backend.call("export", {}, cli_prefix=cli_prefix)
    assert missing["ok"] is False and missing["code"] == 1
    bad_dir = backend.call(
        "export", {"output": str(tmp_path / "no_such_dir" / "a.json")},
        cli_prefix=cli_prefix,
    )
    assert bad_dir["ok"] is False and bad_dir["code"] == 3


def test_unsupported_format_e2e(cli_prefix, project, tmp_path):
    """@expected 不支持的导出格式 → code=7。"""
    env = backend.call(
        "export", {"output": str(tmp_path / "a.obj"), "format": "obj"},
        cli_prefix=cli_prefix,
    )
    assert env["ok"] is False and env["code"] == 7


def test_bad_payload_json_e2e():
    """@expected 机器协议传入非法 JSON → code=1（用法错误）。"""
    proc = _raw(["--json", "project.open", "{not json}"])
    env = _envelope_from(proc)
    assert env["ok"] is False and env["code"] == 1 and proc.returncode == 1


def test_human_readable_output_e2e():
    """@expected 不带 --json 时输出人类可读文本而非 JSON 信封。"""
    proc = _raw(["status"])
    assert proc.returncode == 0
    assert proc.stdout.startswith("[OK]")
    assert "code: 0" in proc.stdout
    with pytest.raises(json.JSONDecodeError):
        json.loads(proc.stdout)


def test_every_command_accepts_json_flag(cli_prefix, project, tmp_path):
    """@expected --json 对全部 action 生效（信封结构齐全）。"""
    payloads = {
        "status": {}, "project.status": {}, "run.bones": {},
        "run.port-check": {"port": 5001},
        "run.frame": {"summary": True}, "run.frames": {"count": 1},
        "export": {"output": str(tmp_path / "all.json")},
        "project.close": {}, "project.open": {"path": project},
        "project.new": {"path": str(tmp_path / "new.csv"), "frames": 1, "force": True},
    }
    for action, payload in payloads.items():
        proc = _raw(["--json", action, json.dumps(payload, ensure_ascii=False)])
        env = _envelope_from(proc)
        assert set(env) == {"ok", "code", "message", "data"}, action
        assert env["ok"] is True, (action, env)
    # run.listen 需要 UDP，单独验证它至少返回合法信封（绑定失败也是合法失败信封）
    proc = _raw(["--json", "run.listen", json.dumps({"seconds": 0.1, "port": 0})])
    env = _envelope_from(proc)
    assert set(env) == {"ok", "code", "message", "data"}


# ── REPL / 主程序分流回归 ───────────────────────────────────────────────

def test_repl_pipe_bom_json_switch_exit_e2e():
    """@expected 管道输入（含 BOM）、json 开关、help、exit 全部正常。"""
    stdin_text = "\ufeffjson on\nstatus\njson off\nhelp\nexit\n"
    proc = _raw(["--repl"], input=stdin_text)
    assert proc.returncode == 0
    assert "json=on" in proc.stdout and "json=off" in proc.stdout
    assert "MotionGlove3DViewer CLI — 命令一览" in proc.stdout
    assert any(
        line.strip().startswith('{"ok": true') for line in proc.stdout.splitlines()
    )


def test_repl_eof_e2e():
    """@expected 无 exit 直接 EOF 也返回 0。"""
    proc = _raw(["--repl"], input="status\n")
    assert proc.returncode == 0


def test_gui_builtin_cli_dispatch_e2e():
    """@expected 主程序 --cli 分流不加载 VTK/PySide6（gui_loaded=false）。"""
    proc = subprocess.run(
        [sys.executable, str(GUI_ENTRY), "--cli", "--json", "status"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=90,
    )
    assert proc.returncode == 0, proc.stderr[-400:]
    env = _envelope_from(proc)
    assert env["ok"] is True and env["data"]["gui_loaded"] is False


@pytest.mark.skipif(
    not _HAS_GUI_DEPS,
    reason="未安装 libs/vtk 与 libs/PySide6，跳过 GUI 普通启动回归",
)
def test_gui_normal_start_regression_e2e():
    """@expected 普通启动（CI 无渲染模式）行为不变，不受 --cli 分流影响。"""
    env = os.environ.copy()
    env["MOTIONGLOVE_CI"] = "1"
    env["MOTIONGLOVE_CI_RENDER"] = "0"
    proc = subprocess.run(
        [sys.executable, str(GUI_ENTRY)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120, env=env,
    )
    assert proc.returncode == 0, proc.stderr[-400:]
