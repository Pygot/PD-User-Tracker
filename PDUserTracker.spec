# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

pytchat_datas, pytchat_binaries, pytchat_hiddenimports = collect_all("pytchat")

a = Analysis(
    ["for_compile.py"],
    pathex=[],
    binaries=pytchat_binaries,
    datas=pytchat_datas,
    hiddenimports=[
        *pytchat_hiddenimports,
        "tkinter",
        "tkinter.ttk",
        "tkinter.messagebox",
        "queue",
        "urllib.request",
        "urllib.error",
        "urllib.parse",
        "json",
        "socket",
        "threading",
        "time",
        "re",
        "pathlib",
        "sys",
        "os",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="PDUserTracker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
