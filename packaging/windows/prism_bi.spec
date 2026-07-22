# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Prism BI Windows portable build (GA 1.0.0).

from pathlib import Path

block_cipher = None
root = Path(SPECPATH).resolve().parents[1]
src = root / "src"

a = Analysis(
    [str(src / "prism_bi" / "main.py")],
    pathex=[str(src)],
    binaries=[],
    datas=[
        (str(src / "prism_bi" / "infrastructure" / "config" / "default_config.toml"),
         "prism_bi/infrastructure/config"),
        (str(src / "prism_bi" / "presentation" / "resources" / "app.qss"),
         "prism_bi/presentation/resources"),
    ],
    hiddenimports=[
        "PySide6.QtCharts",
        "PySide6.QtPrintSupport",
        "duckdb",
        "pyarrow",
        "openpyxl",
        "python_calamine",
        "keyring.backends.Windows",
    ],
    hookspath=[],
    hooksconfig={},
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
    [],
    exclude_binaries=True,
    name="PrismBI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PrismBI",
)
