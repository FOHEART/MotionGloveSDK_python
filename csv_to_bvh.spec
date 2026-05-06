# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['src/csv_to_bvh.py'],
    pathex=['libs', 'src'],
    binaries=[],
    datas=[],
    hiddenimports=['csv_frame_reader', 'definitions', 'xsqeconverter'],
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
    a.binaries,
    a.datas,
    [],
    name='csv_to_bvh',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
