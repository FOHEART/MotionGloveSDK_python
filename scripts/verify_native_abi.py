"""
verify_native_abi.py - 校验 src/native/abi.py 与 MotionGloveSDK_cpp 的二进制布局是否一致

用法：
    python scripts/verify_native_abi.py

原理：用本机编译器（Windows: MSVC / Linux: g++）编译 scripts/lib/abi_probe.cpp，
      让它打印 C++ 侧真实的 sizeof / offsetof，再与 Python 端 ctypes 定义对比。

MotionGloveSDK_cpp 结构体发生改动后，先跑本脚本，再只修改 src/native/abi.py。
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE_SRC = REPO_ROOT / "scripts" / "lib" / "abi_probe.cpp"
INCLUDE_DIR = REPO_ROOT / "third_party" / "MotionGloveSDK_cpp" / "MotionGloveSDK" / "include"
WORK_DIR = REPO_ROOT / "build" / "abi_probe"

_LINE_RE = re.compile(r"^(sizeof|offset):([A-Za-z0-9_]+)\.?([A-Za-z0-9_]*)=(-?\d+)$")

# C++ 结构体名 → src/native/abi.py 中的 ctypes 类名
STRUCT_NAME_MAP = {
    "StreamHeader": "StreamHeader",
    "SingleSkeletonDef": "SingleSkeleton",
    "KHHS42PosAttitude_TypeDef": "KHHS42PosAttitude",
    "KHHS32PosAttitude_TypeDef": "KHHS32PosAttitude",
    "KHHSOpenXRPosAttitude_TypeDef": "KHHSOpenXRPosAttitude",
}


def _normalize(name: str) -> str:
    """去掉下划线与大小写差异，使 C++ camelCase 与 Python snake_case 可比。"""
    return name.replace("_", "").lower()


def _find_vcvars() -> Path | None:
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    vswhere = program_files_x86 / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    if vswhere.is_file():
        result = subprocess.run(
            [str(vswhere), "-latest", "-property", "installationPath"],
            capture_output=True, text=True, check=False,
        )
        install = result.stdout.strip()
        if install:
            candidate = Path(install) / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
            if candidate.is_file():
                return candidate

    for base in (Path(r"C:\Program Files\Microsoft Visual Studio"),):
        if base.is_dir():
            matches = sorted(base.glob("*/VC/Auxiliary/Build/vcvars64.bat"))
            if matches:
                return matches[-1]
    return None


def _build_and_run_probe() -> str:
    if not INCLUDE_DIR.is_dir():
        raise SystemExit(
            f"[error] 未找到 C++ 头文件目录 {INCLUDE_DIR}\n"
            "        请先初始化子模块：git submodule update --init --recursive"
        )

    WORK_DIR.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        vcvars = _find_vcvars()
        if vcvars is None:
            raise SystemExit("[error] 未找到 MSVC 环境（vcvars64.bat），请安装 Visual Studio 2022")
        exe = WORK_DIR / "abi_probe.exe"
        # 通过临时 .bat 组装编译命令，避免 cmd.exe 对多重引号的解析歧义
        batch = WORK_DIR / "run_abi_probe.bat"
        batch.write_text(
            "@echo off\r\n"
            f'call "{vcvars}" >nul\r\n'
            f'cd /d "{WORK_DIR}"\r\n'
            f'cl /nologo /std:c++14 /utf-8 /EHsc /I "{INCLUDE_DIR}" '
            f'"{PROBE_SRC}" /Fe:abi_probe.exe\r\n'
            f'if errorlevel 1 exit /b 1\r\n'
            f'abi_probe.exe\r\n',
            encoding="utf-8",
        )
        result = subprocess.run(
            ["cmd", "/c", str(batch)], capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )
    else:
        compiler = shutil.which("g++") or shutil.which("clang++")
        if compiler is None:
            raise SystemExit("[error] 未找到 g++ / clang++")
        exe = WORK_DIR / "abi_probe"
        build = subprocess.run(
            [compiler, "-std=c++14", f"-I{INCLUDE_DIR}", str(PROBE_SRC), "-o", str(exe)],
            capture_output=True, text=True, check=False,
        )
        if build.returncode != 0:
            raise SystemExit(f"[error] 编译 abi_probe 失败：\n{build.stderr}")
        result = subprocess.run([str(exe)], capture_output=True, text=True, check=False)

    if result.returncode != 0:
        raise SystemExit(f"[error] abi_probe 执行失败：\n{result.stdout}\n{result.stderr}")
    return result.stdout


def _parse_probe_output(output: str) -> dict[str, dict[str, int]]:
    actual: dict[str, dict[str, int]] = {}
    for line in output.splitlines():
        match = _LINE_RE.match(line.strip())
        if not match:
            continue
        kind, struct_name, field_name, value = match.groups()
        entry = actual.setdefault(struct_name, {})
        key = "sizeof" if kind == "sizeof" else field_name
        entry[key] = int(value)
    return actual


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except AttributeError:  # pragma: no cover - 非 TextIOWrapper
        pass

    sys.path.insert(0, str(REPO_ROOT))
    from src.native import abi  # noqa: E402  (需先加入仓库根目录到 sys.path)

    actual = _parse_probe_output(_build_and_run_probe())
    expected = {
        _normalize(struct_name): {_normalize(k): v for k, v in fields.items()}
        for struct_name, fields in abi.describe_layout().items()
    }

    problems: list[str] = []
    for cpp_name, fields in actual.items():
        py_name = STRUCT_NAME_MAP.get(cpp_name)
        if py_name is None:
            problems.append(f"{cpp_name}: scripts/lib/abi_probe.cpp 中的结构体未在 STRUCT_NAME_MAP 登记")
            continue
        py_fields = expected.get(_normalize(py_name))
        if py_fields is None:
            problems.append(f"{cpp_name}: abi.py 中没有对应结构体")
            continue
        for field_name, value in fields.items():
            py_value = py_fields.get(_normalize(field_name))
            if py_value != value:
                label = "sizeof" if field_name == "sizeof" else f"offset({field_name})"
                problems.append(f"{cpp_name}.{label}: C++ = {value}, abi.py = {py_value}")

    for cpp_name in STRUCT_NAME_MAP:
        if cpp_name not in actual:
            problems.append(f"{cpp_name}: scripts/lib/abi_probe.cpp 未输出该结构体")

    if problems:
        print("[fail] src/native/abi.py 与 C++ 布局不一致：")
        for problem in problems:
            print(f"  - {problem}")
        print("\n请更新 src/native/abi.py 中的结构体定义与 EXPECTED_SIZES / EXPECTED_OFFSETS。")
        return 1

    print("[ok] src/native/abi.py 与 MotionGloveSDK_cpp 的二进制布局一致")
    for struct_name, fields in abi.describe_layout().items():
        print(f"  {struct_name}: sizeof = {fields['sizeof']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
