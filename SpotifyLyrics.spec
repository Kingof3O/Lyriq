# -*- mode: python ; coding: utf-8 -*-

datas = [('web', 'web'), ('icon.ico', '.')]
binaries = []
hiddenimports = [
    'clr',
    'pythonnet',
    'webview.platforms.winforms',
    # Only the winsdk namespaces used by media_listener; collecting the full
    # generated package pulls in hundreds of unrelated namespaces.
    'winsdk.windows.media.control',
    'winsdk.windows.storage.streams',
    'winsdk.windows.foundation',
    'winsdk.windows.foundation.collections',
    'winsdk.windows.storage',
    'winsdk.windows.media',
]


a = Analysis(
    ['main.py'],
    pathex=[],
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
    a.binaries,
    a.datas,
    [],
    name='SpotifyLyrics',
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
