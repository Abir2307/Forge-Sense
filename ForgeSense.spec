# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

# Collect everything required by ChromaDB
chroma_datas, chroma_binaries, chroma_hiddenimports = collect_all("chromadb")

a = Analysis(
    ['E:\\Forge-Sense\\safetwin\\app.py'],
    pathex=['E:\\Forge-Sense'],

    binaries=chroma_binaries,

    datas=[
        # Project assets
        ('E:\\Forge-Sense\\assets', 'assets'),
        ('E:\\Forge-Sense\\config', 'config'),
        ('E:\\Forge-Sense\\data', 'data'),

        # Authentication assets
        ('E:\\Forge-Sense\\safetwin\\auth\\assets',
         'safetwin\\auth\\assets'),

        # YOLO model folder
        ('E:\\Forge-Sense\\safetwin\\model',
         'safetwin\\model'),
    ] + chroma_datas,

    hiddenimports=chroma_hiddenimports,

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
    icon='E:\\Forge-Sense\\assets\\logo.ico',
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