"""Festività della Corea del Sud (BDO è un gioco coreano: sapere quando cadono aiuta a
capire i picchi di giocatori/eventi in-game). Lette una tantum da un calendario pubblico
di Google (nessuna chiave richiesta, copre già gli anni fino al 2031) e salvate in
locale: dopo il primo aggiornamento riuscito il calendario resta utilizzabile anche
offline, come il resto del programma."""
import sqlite3
import urllib.error
import urllib.request
from datetime import date

from gilda_app.db.database import get_setting, set_setting

ICS_URL = "https://calendar.google.com/calendar/ical/en.south_korea%23holiday%40group.v.calendar.google.com/public/basic.ics"
HOLIDAY_COLOR = "#c9a227"
LAST_REFRESH_SETTING = "holidays_last_refresh"
# Il feed copre già anni interi in anticipo: un controllo periodico serve solo a
# recepire eventuali correzioni della fonte, non a "non restare senza date".
REFRESH_EVERY_DAYS = 300
FETCH_TIMEOUT_SECONDS = 4


def _unfold_ics_lines(text: str) -> list[str]:
    """Nel formato ICS una riga può continuare su quella dopo se inizia con uno spazio
    (RFC 5545): qui le si ricongiunge prima di leggere i campi."""
    lines: list[str] = []
    for raw_line in text.replace("\r\n", "\n").split("\n"):
        if raw_line[:1] in (" ", "\t") and lines:
            lines[-1] += raw_line[1:]
        else:
            lines.append(raw_line)
    return lines


def parse_ics_holidays(text: str) -> list[tuple[date, str]]:
    """Estrae (data, nome) da ogni VEVENT. Parser minimale apposta: legge solo DTSTART e
    SUMMARY, il feed elenca già una riga per occorrenza (niente RRULE da espandere)."""
    events: list[tuple[date, str]] = []
    current_date: date | None = None
    current_summary: str | None = None
    for line in _unfold_ics_lines(text):
        if line == "BEGIN:VEVENT":
            current_date, current_summary = None, None
        elif line.startswith("DTSTART"):
            digits = line.split(":", 1)[-1].strip()[:8]
            if len(digits) == 8 and digits.isdigit():
                current_date = date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
        elif line.startswith("SUMMARY:"):
            current_summary = line.split(":", 1)[-1].strip()
        elif line == "END:VEVENT" and current_date is not None and current_summary:
            events.append((current_date, current_summary))
    return events


def fetch_holidays() -> list[tuple[date, str]]:
    """Scarica e interpreta il calendario pubblico. Solleva OSError se non raggiungibile
    (nessuna connessione, timeout, sito irraggiungibile): il chiamante decide se ignorare."""
    with urllib.request.urlopen(ICS_URL, timeout=FETCH_TIMEOUT_SECONDS) as response:
        text = response.read().decode("utf-8", errors="replace")
    return parse_ics_holidays(text)


def store_holidays(conn: sqlite3.Connection, holidays: list[tuple[date, str]]) -> None:
    """Sostituisce per intero il contenuto della tabella: è una cache "usa e getta",
    mai modificata a mano dall'utente, quindi ricostruirla da zero è più semplice e
    sicuro di un aggiornamento incrementale."""
    conn.execute("DELETE FROM holidays")
    conn.executemany(
        "INSERT OR IGNORE INTO holidays (date, name) VALUES (?, ?)",
        [(d.isoformat(), name) for d, name in holidays],
    )
    conn.commit()


def get_holidays_in_range(conn: sqlite3.Connection, range_start: date, range_end: date) -> dict[date, list[str]]:
    rows = conn.execute(
        "SELECT date, name FROM holidays WHERE date BETWEEN ? AND ? ORDER BY date",
        (range_start.isoformat(), range_end.isoformat()),
    ).fetchall()
    result: dict[date, list[str]] = {}
    for row in rows:
        result.setdefault(date.fromisoformat(row["date"]), []).append(row["name"])
    return result


def _should_refresh(conn: sqlite3.Connection) -> bool:
    last = get_setting(conn, LAST_REFRESH_SETTING)
    if not last:
        return True
    try:
        last_date = date.fromisoformat(last)
    except ValueError:
        return True
    return (date.today() - last_date).days >= REFRESH_EVERY_DAYS


def refresh_holidays_if_needed(db_path) -> bool:
    """Da chiamare in un thread separato dalla UI (la rete può essere lenta o assente):
    apre una propria connessione perché sqlite3 non permette di condividerne una tra
    thread diversi. Ritorna True solo se ha davvero scaricato dati nuovi, così chi
    l'ha avviata sa se vale la pena aggiornare la vista del calendario."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if not _should_refresh(conn):
            return False
        holidays = fetch_holidays()
        store_holidays(conn, holidays)
        set_setting(conn, LAST_REFRESH_SETTING, date.today().isoformat())
        return True
    except (OSError, urllib.error.URLError):
        return False
    finally:
        conn.close()
