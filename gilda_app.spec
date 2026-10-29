# -*- mode: python ; coding: utf-8 -*-
import glob
import re

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

# Build a onedir (cartella) distribution, non onefile: avvio più veloce e la
# cartella dist/Night_Shade Manager/ può ospitare gilda.db e backups/ accanto all'exe.

# "Carta d'identità" dell'exe (Proprietà -> Dettagli): nome, autore, descrizione, versione. Un exe anonimo, senza
# queste informazioni, è visto con più sospetto dagli antivirus. La versione si legge da gilda_app/version.py (unico
# punto da aggiornare a ogni rilascio): "2.9.2" -> 2.9.2.0.
_version = re.search(r'__version__ = "([^"]+)"', open("gilda_app/version.py", encoding="utf-8").read()).group(1)
_numbers = ([int(n) for n in _version.split(".")] + [0, 0, 0, 0])[:4]
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=tuple(_numbers), prodvers=tuple(_numbers), mask=0x3F, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904B0",  # inglese (USA), Unicode
                    [
                        StringStruct("CompanyName", "Vipp0"),
                        StringStruct("FileDescription", "Night_Shade Manager - gestionale dei membri della gilda"),
                        StringStruct("FileVersion", _version),
                        StringStruct("InternalName", "Night_Shade Manager"),
                        StringStruct("LegalCopyright", "Copyright (c) 2026 Vipp0 - MIT License"),
                        StringStruct("OriginalFilename", "Night_Shade Manager.exe"),
                        StringStruct("ProductName", "Night_Shade Manager"),
                        StringStruct("ProductVersion", _version),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
    ],
)

a = Analysis(
    ["gilda_app/main.py"],
    pathex=[],
    binaries=[],
    # Le PNG delle bandiere e il logo sono dati, non moduli Python: PyInstaller non
    # le include automaticamente seguendo gli import, vanno elencate esplicitamente qui.
    datas=[
        ("gilda_app/resources/flags", "gilda_app/resources/flags"),
        ("gilda_app/resources/app_icon.png", "gilda_app/resources"),
        ("gilda_app/resources/wordmark.png", "gilda_app/resources"),
        ("gilda_app/resources/splash.png", "gilda_app/resources"),
        # Immagini dei temi stagionali (splash_<tema>.png, wordmark_<tema>.png): un tema nuovo non richiede di toccare questo file.
        *[(f, "gilda_app/resources") for f in glob.glob("gilda_app/resources/splash_*.png")],
        *[(f, "gilda_app/resources") for f in glob.glob("gilda_app/resources/wordmark_*.png")],
        *[(f, "gilda_app/resources") for f in glob.glob("gilda_app/resources/deco_*.png")],
        *[(f, "gilda_app/resources") for f in glob.glob("gilda_app/resources/icon_*.png")],
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

# Schermata di avvio mostrata dal bootloader, PRIMA che parta Python: nella fase in cui
# Windows carica le ~1000 librerie dell'app (circa 1 secondo, di più su PC lenti) l'utente
# altrimenti non vede nulla e può credere di non aver cliccato. Viene chiusa dall'app
# appena la finestra è pronta (vedi main.py). Richiede tkinter.
splash = Splash(
    "gilda_app/resources/splash.png",
    binaries=a.binaries,
    datas=a.datas,
    # Sfondo dell'immagine già nero fino ai bordi: niente riquadro chiaro con bordo come
    # nella vecchia splash, sarebbe stonato. Il testo "Loading..." animato (vedi
    # main.py) si sovrappone nello spazio vuoto sotto al logo.
    # text_pos ancora l'angolo in basso a sinistra del testo (limite della Splash di
    # PyInstaller: text_justify riguarda solo il testo su più righe, non la posizione).
    # x calcolata misurando con Tk la larghezza di "Loading."/".."/"..." a questa
    # dimensione, per restare centrata sull'immagine (720px) nonostante il testo cambi
    # larghezza mentre i puntini si animano.
    text_pos=(321, 510),
    text_size=14,
    text_color="#e6d9ff",
    text_default="Loading...",
    text_justify="center",
    always_on_top=False,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    [],
    exclude_binaries=True,
    name="Night_Shade Manager",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon="gilda_app/resources/app_icon.ico",
    version=version_info,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    splash.binaries,
    strip=False,
    upx=False,
    name="Night_Shade Manager",
)
