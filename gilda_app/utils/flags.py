"""Mappa nome nazione (come compare nel file Excel) -> bandiera e nome canonico.

Le bandiere sono PNG bundlate in gilda_app/resources/flags/<alpha2>.png (generate una
tantum con scripts/extract_flags.py) invece delle emoji Unicode: i simboli "regional
indicator" richiedono un font e uno shaping engine capaci di comporli in un'unica
bandiera, supporto che Qt su Windows non garantisce in modo affidabile."""
from pathlib import Path

import pycountry
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap

# Alias per nomi che non combaciano esattamente con pycountry (typo, forme brevi, non-stati)
# raccolti ispezionando i valori di Nation realmente presenti in List 2026.xlsx.
_ALIASES = {
    "uk": "United Kingdom",
    "scotland": "United Kingdom",
    "usa": "United States",
    "dubai": "United Arab Emirates",
    "uae": "United Arab Emirates",
    "ksa": "Saudi Arabia",
    "saudi": "Saudi Arabia",
    "arabia": "Saudi Arabia",
    "united saudi arabia": "Saudi Arabia",
    "russia": "Russian Federation",
    "south korea": "Korea, Republic of",
    "korea": "Korea, Republic of",
    "iran": "Iran, Islamic Republic of",
    "vietnam": "Viet Nam",
    "bolivia": "Bolivia, Plurinational State of",
    "venezuela": "Venezuela, Bolivarian Republic of",
    "moldova": "Moldova, Republic of",
    "czech republic": "Czechia",
    "czech": "Czechia",
    "turkey": "Türkiye",
    "turkiye": "Türkiye",
    "franc": "France",
    "jap": "Japan",
    "netherland": "Netherlands",
    "portgal": "Portugal",
    "switz": "Switzerland",
    "thai": "Thailand",
    "bosnia": "Bosnia and Herzegovina",
    "palestine": "Palestine, State of",
}

FLAGS_DIR = Path(__file__).resolve().parent.parent / "resources" / "flags"

_alpha2_cache: dict[str, str | None] = {}
_pixmap_cache: dict[str, QPixmap | None] = {}


def _alpha2_for(nation: str) -> str | None:
    key = nation.strip().lower()
    if not key:
        return None
    if key in _alpha2_cache:
        return _alpha2_cache[key]

    lookup_name = _ALIASES.get(key, nation.strip())
    try:
        alpha2 = pycountry.countries.lookup(lookup_name).alpha_2
    except LookupError:
        alpha2 = None

    _alpha2_cache[key] = alpha2
    return alpha2


def flag_pixmap(nation: str) -> QPixmap | None:
    """Ritorna la bandiera come QPixmap, o None se la nazione non è riconosciuta o non ha un'immagine."""
    alpha2 = _alpha2_for(nation)
    if not alpha2:
        return None
    if alpha2 not in _pixmap_cache:
        path = FLAGS_DIR / f"{alpha2}.png"
        pixmap = QPixmap(str(path)) if path.exists() else None
        _pixmap_cache[alpha2] = pixmap if pixmap and not pixmap.isNull() else None
    return _pixmap_cache[alpha2]


def combined_flag_icon(nations: list[str]) -> QIcon | None:
    """Combina una o due bandiere affiancate in un'unica icona (per doppia nazionalità)."""
    pixmaps = [p for n in nations if (p := flag_pixmap(n)) is not None]
    if not pixmaps:
        return None

    spacing = 3
    height = max(p.height() for p in pixmaps)
    width = sum(p.width() for p in pixmaps) + spacing * (len(pixmaps) - 1)

    canvas = QPixmap(width, height)
    canvas.fill(Qt.transparent)
    painter = QPainter(canvas)
    x = 0
    for pixmap in pixmaps:
        painter.drawPixmap(x, (height - pixmap.height()) // 2, pixmap)
        x += pixmap.width() + spacing
    painter.end()

    return QIcon(canvas)


def nations_text(nations: list[str]) -> str:
    """Testo per la colonna Nation (l'icona bandiera viene impostata separatamente sulla cella)."""
    return " / ".join(nations)
