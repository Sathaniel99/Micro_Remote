# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: ejecutable del receptor.
# Genera dist/receptor.exe. Uso: pyinstaller --noconfirm --clean receptor.spec

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH)
SOUNDDEVICE_DATA = collect_data_files(
    "_sounddevice_data", includes=["portaudio-binaries/*.dll"]
)

a = Analysis(
    ['interface_receptor.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'icons'), 'icons'),
        (str(ROOT / 'micro_remote' / 'assets'), 'micro_remote/assets'),
    ] + SOUNDDEVICE_DATA,
    hiddenimports=['sounddevice', '_sounddevice_data'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'matplotlib', 'PIL', 'pytest', 'tests'],
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
    name='receptor',
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
    icon=[str(ROOT / 'icons' / 'ico' / 'receptor.ico')],
)
