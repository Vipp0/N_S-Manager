"""Compleanno di un membro: si salva come "MM-DD" (anno non indicato) oppure "YYYY-MM-DD".
L'anno è facoltativo: non tutti vogliono comunicarlo, e per gli auguri bastano giorno e mese."""
from datetime import date

MIN_YEAR = 1900


def build_birthday(day: int, month: int, year_text: str) -> str | None:
    """None se giorno e mese sono vuoti (0). ValueError se il valore non è valido: un
    solo dei due indicato, giorno inesistente nel mese (29 febbraio ammesso), anno
    incompleto o fuori intervallo."""
    year_text = year_text.strip()
    if not day and not month:
        if year_text:
            raise ValueError("year without day/month")
        return None
    if not day or not month:
        raise ValueError("incomplete day/month")
    if year_text:
        if not year_text.isdigit() or len(year_text) != 4:
            raise ValueError("bad year")
        year = int(year_text)
        if year < MIN_YEAR or year > date.today().year:
            raise ValueError("year out of range")
        date(year, month, day)  # ValueError per giorni inesistenti (es. 31-04, 29-02 non bisestile)
        return f"{year:04d}-{month:02d}-{day:02d}"
    date(2000, month, day)  # anno bisestile: il 29 febbraio senza anno è valido
    return f"{month:02d}-{day:02d}"


def split_birthday(value: str | None) -> tuple[int, int, int | None] | None:
    """(giorno, mese, anno o None) da un valore salvato, None se assente o illeggibile."""
    if not value:
        return None
    parts = value.split("-")
    try:
        if len(parts) == 2:
            return int(parts[1]), int(parts[0]), None
        if len(parts) == 3:
            return int(parts[2]), int(parts[1]), int(parts[0])
    except ValueError:
        return None
    return None


def next_birthday(value: str | None, today: date) -> tuple[date, int | None] | None:
    """(prossima data di compleanno da oggi in poi, età che si compie se l'anno è noto)."""
    parts = split_birthday(value)
    if parts is None:
        return None
    day, month, year = parts
    for candidate_year in (today.year, today.year + 1):
        try:
            when = date(candidate_year, month, day)
        except ValueError:  # 29 febbraio in un anno non bisestile
            when = date(candidate_year, 2, 28)
        if when >= today:
            return when, (candidate_year - year if year else None)
    return None
