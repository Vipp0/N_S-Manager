"""Formato date mostrato all'utente (dd-mm-yyyy, come in Italia).

Nel database le date restano salvate come yyyy-mm-dd: in quel formato si ordinano
correttamente come testo (ORDER BY changed_at, sorted() sui mesi in stats.py), cosa che
dd-mm-yyyy non garantirebbe. La conversione avviene solo al momento di mostrare la data.
"""

DISPLAY_DATE_QT_FORMAT = "dd-MM-yyyy"


def iso_to_display(iso: str) -> str:
    """'2025-03-07' o '2025-03-07 10:20:00' -> '07-03-2025'."""
    year, month, day = iso[:10].split("-")
    return f"{day}-{month}-{year}"


def iso_month_to_display(iso_month: str) -> str:
    """'2025-03' -> '03-2025'."""
    year, month = iso_month[:7].split("-")
    return f"{month}-{year}"
