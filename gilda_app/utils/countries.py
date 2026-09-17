"""Elenco di tutte le nazioni per i menu a tendina di selezione nazionalità,
nella lingua corrente dell'interfaccia. Il valore salvato nel database resta
sempre il nome inglese canonico (pycountry), per coerenza con i dati storici
e con la risoluzione delle bandiere in gilda_app/utils/flags.py."""
import pycountry

from gilda_app.i18n import get_language
from gilda_app.utils.flags import translate_country_name

_EN_NAMES: dict[str, str] = {country.alpha_2: country.name for country in pycountry.countries}
_IT_NAMES: dict[str, str] = {alpha2: translate_country_name(name, "it") for alpha2, name in _EN_NAMES.items()}

_NAME_TO_ALPHA2: dict[str, str] = {}
for _alpha2, _name in {**_EN_NAMES, **_IT_NAMES}.items():
    _NAME_TO_ALPHA2.setdefault(_name, _alpha2)

ALL_COUNTRIES = sorted(_EN_NAMES.values())


def country_choices() -> list[str]:
    """Nomi nazione nella lingua corrente, ordinati alfabeticamente."""
    names = _IT_NAMES.values() if get_language() == "it" else _EN_NAMES.values()
    return sorted(names)


def canonical_name(display_name: str) -> str:
    """Converte un nome mostrato (in italiano o inglese) nel nome inglese canonico da salvare.
    Testo libero non riconosciuto viene lasciato invariato."""
    alpha2 = _NAME_TO_ALPHA2.get(display_name.strip())
    return _EN_NAMES[alpha2] if alpha2 else display_name
