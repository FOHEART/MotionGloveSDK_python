# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

# 打包时必须带上 C++ MotionGloveSDK 动态库（数据流解析由它完成）
_ROOT = Path(SPECPATH)
sys.path.insert(0, str(_ROOT))
from src.native.loader import find_library  # noqa: E402

try:
    _native_lib = find_library()
except Exception as exc:  # noqa: BLE001 - 打包前必须明确失败
    raise SystemExit(
        "[spec] 未找到 MotionGloveSDK 原生库，请先编译 third_party/MotionGloveSDK_cpp："
        "scripts\\[Windows]build_mgsdk_cpp.cmd 或 bash \"scripts/[Linux]build_mgsdk_cpp.sh\"\n" + str(exc)
    )

datas = [('tools/fonts', 'tools/fonts'), ('ui', 'ui')]
binaries = [(_native_lib, '.')]
hiddenimports = ['vtkmodules.all', 'vtkmodules.qt.QVTKRenderWindowInteractor', 'PySide6.QtWidgets', 'PySide6.QtCore', 'PySide6.QtGui']
tmp_ret = collect_all('vtk')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('vtkmodules')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PySide6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['motionGloveSDK_example3_3dView.py'],
    pathex=['libs', 'python_draw3d', 'ui'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MotionGlove3DViewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MotionGlove3DViewer',
)
