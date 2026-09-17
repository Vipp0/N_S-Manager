"""Mappa nome nazione (come compare nel file Excel) -> emoji bandiera."""
import pycountry

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

_cache: dict[str, str | None] = {}


def _alpha2_for(nation: str) -> str | None:
    key = nation.strip().lower()
    if not key:
        return None

    lookup_name = _ALIASES.get(key, nation.strip())

    try:
        result = pycountry.countries.lookup(lookup_name)
        return result.alpha_2
    except LookupError:
        return None


def flag_emoji(nation: str) -> str:
    """Ritorna l'emoji bandiera per una nazione, o stringa vuota se non riconosciuta."""
    if nation not in _cache:
        alpha2 = _alpha2_for(nation)
        if alpha2:
            _cache[nation] = "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in alpha2.upper())
        else:
            _cache[nation] = None
    return _cache[nation] or ""


def flags_and_text(nations: list[str]) -> str:
    """Testo per la colonna Nation: bandiera/e affiancate + nomi, per righe con doppia nazionalità."""
    if not nations:
        return ""
    parts = [f"{flag_emoji(n)} {n}".strip() for n in nations]
    return " / ".join(parts)
