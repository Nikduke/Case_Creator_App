# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files


extra_binaries = []
conda_library_bin = Path(sys.prefix) / "Library" / "bin"
for dll_name in (
    "ffi-8.dll",
    "libbz2.dll",
    "libcrypto-3-x64.dll",
    "libexpat.dll",
    "libssl-3-x64.dll",
):
    dll_path = conda_library_bin / dll_name
    if dll_path.exists():
        extra_binaries.append((str(dll_path), "."))

asset_datas = collect_data_files("case_builder_app.assets")
icon_path = Path("src") / "case_builder_app" / "assets" / "mpe_app_icon.ico"

a = Analysis(
    ['src\\case_builder_app\\__main__.py'],
    pathex=['src'],
    binaries=extra_binaries,
    datas=asset_datas,
    hiddenimports=[
        "pyexpat",
        "xml.parsers.expat",
    ],
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
    name='Case_Creator_App',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon=str(icon_path),
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
