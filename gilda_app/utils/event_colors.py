"""Colori prefissati per gli eventi del calendario (scelta fissa, niente colori liberi:
è più facile associare un colore a un tipo di evento e riconoscerlo a colpo d'occhio)."""
from PySide6.QtGui import QColor

# (chiave i18n del nome, colore esadecimale). L'ordine è quello mostrato nel form.
EVENT_COLORS: list[tuple[str, str]] = [
    ("color.red", "#d13438"),
    ("color.orange", "#f7630c"),
    ("color.yellow", "#e6b800"),
    ("color.lime", "#7cb342"),
    ("color.green", "#2e9d4f"),
    ("color.teal", "#00897b"),
    ("color.cyan", "#00a3c4"),
    ("color.blue", "#0f6cbd"),
    ("color.indigo", "#3f51b5"),
    ("color.purple", "#8a3ffc"),
    ("color.magenta", "#ad1457"),
    ("color.pink", "#e3428e"),
    ("color.brown", "#8b5a2b"),
    ("color.gray", "#7a7a7a"),
    ("color.black", "#1f1f1f"),
]

DEFAULT_EVENT_COLOR = "#0f6cbd"


def nearest_preset(hex_color: str) -> str:
    """Colore prefissato più vicino a uno qualsiasi: serve per gli eventi creati quando
    i colori erano liberi, così modificandoli si ritrovano su uno dei colori della lista."""
    target = QColor(hex_color)
    if not target.isValid():
        return DEFAULT_EVENT_COLOR

    def distance(preset_hex: str) -> int:
        c = QColor(preset_hex)
        return (c.red() - target.red()) ** 2 + (c.green() - target.green()) ** 2 + (c.blue() - target.blue()) ** 2

    return min((hex_ for _, hex_ in EVENT_COLORS), key=distance)
