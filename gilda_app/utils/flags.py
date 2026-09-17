"""Mappa nome nazione (come compare nel file Excel) -> bandiera e nome canonico.

Le bandiere sono PNG bundlate in gilda_app/resources/flags/<alpha2>.png (generate una
tantum con scripts/extract_flags.py) invece delle emoji Unicode: i simboli "regional
indicator" richiedono un font e uno shaping engine capaci di comporli in un'unica
bandiera, supporto che Qt su Windows non garantisce in modo affidabile."""
import gettext
from pathlib import Path

import pycountry
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

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

# Dimensioni native delle PNG in FLAGS_DIR (vedi scripts/extract_flags.py) e spaziatura
# usata quando se ne affiancano due per la doppia nazionalità: esposte qui perché
# member_table.py deve impostare l'iconSize della tabella sullo stesso valore, per
# evitare che Qt debba scalare (e quindi sfocare) l'icona più grande possibile (2 bandiere).
FLAG_WIDTH = 48
FLAG_HEIGHT = 32
FLAG_SPACING = 3
MAX_FLAG_ICON_SIZE = (FLAG_WIDTH * 2 + FLAG_SPACING, FLAG_HEIGHT)

_alpha2_cache: dict[str, str | None] = {}
_pixmap_cache: dict[str, QPixmap | None] = {}
_generic_pixmap: QPixmap | None = None
_it_translation: gettext.NullTranslations | None = None


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


def _italian_translation() -> gettext.NullTranslations:
    global _it_translation
    if _it_translation is None:
        try:
            _it_translation = gettext.translation("iso3166-1", pycountry.LOCALES_DIR, languages=["it"])
        except OSError:
            _it_translation = gettext.NullTranslations()
    return _it_translation


def translate_country_name(english_name: str, lang: str) -> str:
    """Traduce un nome nazione canonico (inglese, pycountry) nella lingua richiesta."""
    if lang == "it":
        return _italian_translation().gettext(english_name)
    return english_name


def display_nation(nation: str) -> str:
    """Nome nazione nella lingua corrente dell'app, risolvendo alias/typo quando possibile.
    Se la nazione non è vuota ma non è riconosciuta (dato sporco), ritorna "Sconosciuta"/"Unknown"
    invece del testo grezzo salvato."""
    from gilda_app.i18n import get_language, tr  # import qui per evitare un ciclo a livello di modulo

    alpha2 = _alpha2_for(nation)
    if not alpha2:
        return tr("nation.unknown") if nation.strip() else nation
    country = pycountry.countries.get(alpha_2=alpha2)
    return translate_country_name(country.name, get_language())


def _generic_flag_pixmap() -> QPixmap:
    """Bandierina segnaposto (bianca con bordo) per nazioni non riconosciute."""
    global _generic_pixmap
    if _generic_pixmap is None:
        width, height = FLAG_WIDTH, FLAG_HEIGHT
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.white)
        painter = QPainter(pixmap)
        pen = QPen(QColor(190, 190, 190))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawRect(0, 0, width - 1, height - 1)
        painter.end()
        _generic_pixmap = pixmap
    return _generic_pixmap


def flag_pixmap(nation: str) -> QPixmap:
    """Ritorna la bandiera come QPixmap; una bandierina generica se la nazione non è riconosciuta."""
    alpha2 = _alpha2_for(nation)
    if alpha2 and alpha2 not in _pixmap_cache:
        path = FLAGS_DIR / f"{alpha2}.png"
        pixmap = QPixmap(str(path)) if path.exists() else None
        _pixmap_cache[alpha2] = pixmap if pixmap and not pixmap.isNull() else None

    resolved = _pixmap_cache.get(alpha2) if alpha2 else None
    return resolved if resolved is not None else _generic_flag_pixmap()


def combined_flag_icon(nations: list[str]) -> QIcon | None:
    """Combina una o due bandiere affiancate in un'unica icona (per doppia nazionalità).
    Ritorna None solo se non è stata indicata nessuna nazione."""
    if not nations:
        return None

    pixmaps = [flag_pixmap(n) for n in nations]

    height = max(p.height() for p in pixmaps)
    width = sum(p.width() for p in pixmaps) + FLAG_SPACING * (len(pixmaps) - 1)

    canvas = QPixmap(width, height)
    canvas.fill(Qt.transparent)
    painter = QPainter(canvas)
    x = 0
    for pixmap in pixmaps:
        painter.drawPixmap(x, (height - pixmap.height()) // 2, pixmap)
        x += pixmap.width() + FLAG_SPACING
    painter.end()

    return QIcon(canvas)


def nations_text(nations: list[str]) -> str:
    """Testo per la colonna Nation, nella lingua corrente (l'icona bandiera è separata)."""
    return " / ".join(display_nation(n) for n in nations)
