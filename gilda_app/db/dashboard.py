"""Query di sola lettura per i riquadri della dashboard."""
import sqlite3
from datetime import date, timedelta

from gilda_app.db.calendar_events import get_all_events, occurrences_in_range
from gilda_app.db.holidays import get_holidays_in_range
from gilda_app.models.member import STATUS_ATTIVO

RECENT_DAYS = 30
AGENDA_DAYS = 7


def recent_transitions(conn: sqlite3.Connection, limit: int = 4) -> list[sqlite3.Row]:
    """Ultimi cambi di lista veri (uscite, rientri, ban). Gli "ingressi" iniziali sono
    esclusi: un import senza date li registra tutti nello stesso istante e
    riempirebbero l'elenco di rumore."""
    return conn.execute(
        """
        SELECT h.changed_at, h.previous_status, h.new_status, m.family_name
        FROM status_history h JOIN members m ON m.id = h.member_id
        WHERE h.previous_status IS NOT NULL AND h.changed_at IS NOT NULL
        ORDER BY h.changed_at DESC, h.id DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()


def transitions_to(conn: sqlite3.Connection, status: str, days: int = RECENT_DAYS) -> int:
    """Quanti membri sono passati a `status` negli ultimi `days` giorni (solo cambi di lista)."""
    return conn.execute(
        "SELECT COUNT(*) FROM status_history WHERE previous_status IS NOT NULL "
        "AND new_status = ? AND changed_at >= datetime('now', ?)",
        (status, f"-{days} days"),
    ).fetchone()[0]


def joined_recently(conn: sqlite3.Connection, days: int = RECENT_DAYS) -> int:
    """Ingressi negli ultimi `days` giorni: la data di ingresso registrata e i rientri (da ex membro o
    da bannato a membro attuale), che sono ingressi a tutti gli effetti."""
    first = conn.execute(
        "SELECT COUNT(*) FROM members WHERE data_inserimento IS NOT NULL "
        "AND data_inserimento >= date('now', ?)",
        (f"-{days} days",),
    ).fetchone()[0]
    return first + transitions_to(conn, STATUS_ATTIVO, days)


def upcoming_agenda(conn: sqlite3.Connection, today: date, days: int = AGENDA_DAYS) -> list[tuple[date, str, bool]]:
    """(data, titolo, è_festività) da oggi ai prossimi `days` giorni, in ordine di data."""
    end = today + timedelta(days=days - 1)
    items: list[tuple[date, str, bool]] = []
    for row in get_all_events(conn):
        for occurrence in occurrences_in_range(row, today, end):
            items.append((occurrence, row["title"], False))
    for day, names in get_holidays_in_range(conn, today, end).items():
        for name in names:
            items.append((day, name, True))
    return sorted(items, key=lambda item: (item[0], item[2]))


def recent_joins(conn: sqlite3.Connection, limit: int = 5) -> list[dict]:
    """Ultimi ingressi tra i membri attuali. Per ognuno vale la data più recente tra l'ingresso registrato
    e l'ultimo rientro (da ex membro o da bannato): chi è rientrato compare con la data del rientro e
    `rejoined` vero. Dict con family_name, main_name, joined_on (yyyy-mm-dd), rejoined."""
    rows = conn.execute(
        """
        SELECT m.id, m.family_name, m.main_name, m.data_inserimento,
               (SELECT MAX(h.changed_at) FROM status_history h
                WHERE h.member_id = m.id AND h.new_status = 'attivo' AND h.previous_status IN ('ex_membro', 'bannato')
                  AND h.changed_at IS NOT NULL) AS rejoined_at
        FROM members m WHERE m.status = 'attivo'
        """
    ).fetchall()
    joins = []
    for row in rows:
        first = row["data_inserimento"][:10] if row["data_inserimento"] else None
        rejoin = row["rejoined_at"][:10] if row["rejoined_at"] else None
        if first is None and rejoin is None:
            continue
        rejoined = rejoin is not None and (first is None or rejoin >= first)
        joins.append(
            {
                "id": row["id"],
                "family_name": row["family_name"],
                "main_name": row["main_name"],
                "joined_on": rejoin if rejoined else first,
                "rejoined": rejoined,
            }
        )
    joins.sort(key=lambda j: (j["joined_on"], j["id"]), reverse=True)
    return joins[:limit]
