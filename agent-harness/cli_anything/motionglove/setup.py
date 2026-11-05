"""@brief cli-anything-motionglove 的 pip 安装配置（支持 pip install -e .）。

@details
在本目录执行 `pip install -e .` 后可用命令 `cli-anything-motionglove`。
setup.py 与 _cli.py / utils/ 位于同一目录，editable 安装会把该目录加入
sys.path，因此用 py_modules + 顶层 utils 包即可可靠导入；
这比把 package_dir 指向父目录更兼容旧版 setuptools 的 develop 模式。
harness 是 Agent 侧开发工具，只有 click 一个依赖；运行时 SDK 依赖
（vtk/PySide6 等）仍按 AGENTS.md 约定装到仓库 libs/。
"""

from setuptools import setup

setup(
    name="cli-anything-motionglove",
    version="1.0.0",
    description="CLI-Anything harness for MotionGlove3DViewer / MotionGloveSDK CLI",
    python_requires=">=3.10",
    py_modules=["_cli"],
    packages=["utils"],
    install_requires=["click>=8.0"],
    entry_points={
        "console_scripts": [
            "cli-anything-motionglove=_cli:main",
        ],
    },
)
