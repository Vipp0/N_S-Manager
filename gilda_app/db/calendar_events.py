"""Eventi del calendario: CRUD e calcolo delle occorrenze di una serie ricorrente.

Un evento ricorrente è una riga sola; modificarlo o cancellarlo agisce sull'intera
serie (niente eccezioni per singola data). Le occorrenze visibili si calcolano al
volo con occurrences_in_range, senza salvarle una per una."""
import calendar
import sqlite3
from datetime import date, timedelta

RECURRENCE_NONE = "none"
RECURRENCE_DAILY = "daily"
RECURRENCE_WEEKLY = "weekly"
RECURRENCE_MONTHLY = "monthly"

# Tetto di sicurezza sulle iterazioni per una ricorrenza mensile, che non ha un passo
# fisso in giorni e va quindi percorsa mese per mese.
_MAX_MONTHLY_STEPS = 2400


def add_event(
    conn: sqlite3.Connection,
    start_date: str,
    title: str,
    color: str,
    note: str | None = None,
    recurrence_unit: str = RECURRENCE_NONE,
    recurrence_interval: int = 1,
    recurrence_end_date: str | None = None,
    commit: bool = True,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO calendar_events
            (start_date, title, note, color, recurrence_unit, recurrence_interval, recurrence_end_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (start_date, title, note, color, recurrence_unit, max(1, recurrence_interval), recurrence_end_date),
    )
    if commit:
        conn.commit()
    return cur.lastrowid


def update_event(
    conn: sqlite3.Connection,
    event_id: int,
    start_date: str,
    title: str,
    color: str,
    note: str | None = None,
    recurrence_unit: str = RECURRENCE_NONE,
    recurrence_interval: int = 1,
    recurrence_end_date: str | None = None,
    commit: bool = True,
) -> None:
    conn.execute(
        """
        UPDATE calendar_events
        SET start_date = ?, title = ?, note = ?, color = ?,
            recurrence_unit = ?, recurrence_interval = ?, recurrence_end_date = ?
        WHERE id = ?
        """,
        (start_date, title, note, color, recurrence_unit, max(1, recurrence_interval), recurrence_end_date, event_id),
    )
    if commit:
        conn.commit()


def delete_event(conn: sqlite3.Connection, event_id: int) -> None:
    conn.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
    conn.commit()


def get_all_events(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM calendar_events ORDER BY start_date, id").fetchall()


def _add_months(d: date, months: int) -> date:
    """Somma mesi a una data; se il giorno non esiste nel mese di arrivo (es. 31 in un
    mese da 30) si ferma all'ultimo giorno di quel mese."""
    total = d.year * 12 + (d.month - 1) + months
    year, month = divmod(total, 12)
    month += 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day))


def occurrences_in_range(row, range_start: date, range_end: date) -> list[date]:
    """Date concrete di una serie comprese tra range_start e range_end (estremi inclusi).

    `row` è una riga di calendar_events (o qualsiasi mapping con le stesse chiavi)."""
    start = date.fromisoformat(row["start_date"])
    end_cap = date.fromisoformat(row["recurrence_end_date"]) if row["recurrence_end_date"] else None
    unit = row["recurrence_unit"]
    interval = max(1, row["recurrence_interval"])

    last = range_end if end_cap is None else min(range_end, end_cap)
    if start > last:
        return []

    if unit == RECURRENCE_NONE:
        return [start] if range_start <= start <= last else []

    if unit in (RECURRENCE_DAILY, RECURRENCE_WEEKLY):
        step = timedelta(days=interval * (7 if unit == RECURRENCE_WEEKLY else 1))
        # Salta direttamente vicino a range_start invece di iterare dalla data di
        # partenza: resta veloce anche per una serie iniziata molto tempo prima.
        if start < range_start:
            steps_to_skip = (range_start - start) // step
            current = start + step * steps_to_skip
        else:
            current = start
        result = []
        while current <= last:
            if current >= range_start:
                result.append(current)
            current += step
        return result

    if unit == RECURRENCE_MONTHLY:
        result = []
        for n in range(_MAX_MONTHLY_STEPS):
            current = _add_months(start, n * interval)
            if current > last:
                break
            if current >= range_start:
                result.append(current)
        return result

    return []
