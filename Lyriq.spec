# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('web', 'web'), ('icon.ico', '.')],
    hiddenimports=['clr', 'pythonnet', 'webview.platforms.winforms', 'pycaw', 'comtypes', 'winsdk.windows.media.control', 'winsdk.windows.storage.streams', 'winsdk.windows.foundation', 'winsdk.windows.foundation.collections', 'winsdk.windows.storage', 'winsdk.windows.media'],
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
    name='Lyriq',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
