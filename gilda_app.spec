# -*- mode: python ; coding: utf-8 -*-
# Build a onedir (cartella) distribution, non onefile: avvio più veloce e la
# cartella dist/GestionaleGilda/ può ospitare gilda.db e backups/ accanto all'exe.

a = Analysis(
    ["gilda_app/main.py"],
    pathex=[],
    binaries=[],
    # Le PNG delle bandiere sono dati, non moduli Python: PyInstaller non le include
    # automaticamente seguendo gli import, vanno elencate esplicitamente qui.
    datas=[("gilda_app/resources/flags", "gilda_app/resources/flags")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GestionaleGilda",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="GestionaleGilda",
)
