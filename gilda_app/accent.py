"""Colore d'accento di pulsanti ed evidenziazioni: il viola Night Shade di base, più altri quattro da scegliere in
Impostazioni. Nei periodi di festa lo sostituisce il colore del tema stagionale (vedi seasons.py), poi torna
quello scelto. Verde, ambra e rosso restano fuori dalla scelta: nel programma significano ingresso, avviso, ban."""

ACCENT_SETTING = "accent_color"
DEFAULT_ACCENT_KEY = "violet"
# chiave -> colore; l'ordine è quello delle pastiglie in Impostazioni
ACCENT_COLORS = {
    "violet": "#6d4bd1",
    "teal": "#009faa",  # l'azzurro-turchese usato fino alla 2.9
    "blue": "#2a6fdb",
    "fuchsia": "#c2308a",
    "slate": "#52627a",
}


def accent_hex(key: str | None) -> str:
    """Il colore della chiave salvata; una chiave sconosciuta (database di un'altra versione) vale il predefinito."""
    return ACCENT_COLORS.get(key or "", ACCENT_COLORS[DEFAULT_ACCENT_KEY])
