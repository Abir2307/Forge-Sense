# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['E:\\Forge-Sense\\safetwin\\app.py'],
    pathex=[],
    binaries=[],
    datas=[('E:\\Forge-Sense\\safetwin\\auth\\assets', './safetwin/auth/assets'), ('E:\\Forge-Sense\\assets', './assets'), ('E:\\Forge-Sense\\config', './config'), ('E:\\Forge-Sense\\data', './data')],
    hiddenimports=[],
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
    name='ForgeSense',
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
    name='ForgeSense',
)
