# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\Kauan Lauer\\Documents\\Scripts\\HeadToys\\uninstaller_app.py'],
    pathex=['C:\\Users\\Kauan Lauer\\Documents\\Scripts\\HeadToys\\src'],
    binaries=[],
    datas=[],
    hiddenimports=['darkdetect', 'pythoncom', 'pywintypes', 'win32timezone'],
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
    name='HeadToys Uninstall',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\Kauan Lauer\\Documents\\Scripts\\HeadToys\\logo_buscador.ico'],
)
