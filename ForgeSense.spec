# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

# Collect all dynamically imported ChromaDB modules, binaries and data
chroma_datas, chroma_binaries, chroma_hiddenimports = collect_all("chromadb")

# ---------------------------------------------------------------------
# Project Assets
# ---------------------------------------------------------------------

project_datas = [
    ("E:\\Forge-Sense\\safetwin\\auth\\assets", "safetwin/auth/assets"),
    ("E:\\Forge-Sense\\assets", "assets"),
    ("E:\\Forge-Sense\\config", "config"),
    ("E:\\Forge-Sense\\data", "data"),
]

# Merge with ChromaDB resources
datas = project_datas + chroma_datas
binaries = chroma_binaries
hiddenimports = chroma_hiddenimports

# ---------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------

a = Analysis(
    ["E:\\Forge-Sense\\safetwin\\app.py"],
    pathex=["E:\\Forge-Sense"],
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

# ---------------------------------------------------------------------
# Python Archive
# ---------------------------------------------------------------------

pyz = PYZ(a.pure)

# ---------------------------------------------------------------------
# Executable
# ---------------------------------------------------------------------

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ForgeSense",
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
    icon="E:\\Forge-Sense\\assets\\logo.ico",
)

# ---------------------------------------------------------------------
# Distribution Folder
# ---------------------------------------------------------------------

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ForgeSense",
)