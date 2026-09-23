# -*- mode: python ; coding: utf-8 -*-
# Build a onedir (cartella) distribution, non onefile: avvio più veloce e la
# cartella dist/Night_Shade Manager/ può ospitare gilda.db e backups/ accanto all'exe.

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
