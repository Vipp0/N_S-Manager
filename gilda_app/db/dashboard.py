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


MOVE_JOINED = "joined"
MOVE_REJOINED = "rejoined"
MOVE_LEFT = "left"
MOVE_BANNED = "banned"


def recent_movements(conn: sqlite3.Connection, limit: int = 5) -> list[dict]:
    """Gli ultimi movimenti in gilda, uno per membro (il più recente): ingresso (data registrata, solo per chi
    è tra i membri attuali), rientro (da ex membro o da bannato a membro attuale), uscita (da membro attuale a
    ex membro) e ban. Gli altri passaggi, tra ex membro e bannato, non contano.
    Dict con id, family_name, main_name, day (yyyy-mm-dd), kind (MOVE_*)."""
    latest: dict[int, tuple[tuple, dict]] = {}

    def consider(member_id, family_name, main_name, day, kind, order) -> None:
        key = (day, order)
        if member_id not in latest or key > latest[member_id][0]:
            latest[member_id] = (
                key,
                {"id": member_id, "family_name": family_name, "main_name": main_name, "day": day, "kind": kind},
            )

    for row in conn.execute(
        "SELECT id, family_name, main_name, data_inserimento FROM members "
        "WHERE status = 'attivo' AND data_inserimento IS NOT NULL"
    ):
        consider(row["id"], row["family_name"], row["main_name"], row["data_inserimento"][:10], MOVE_JOINED, (0, 0))
    for row in conn.execute(
        """
        SELECT h.id AS history_id, h.changed_at, h.previous_status, h.new_status,
               m.id, m.family_name, m.main_name
        FROM status_history h JOIN members m ON m.id = h.member_id
        WHERE h.previous_status IS NOT NULL AND h.changed_at IS NOT NULL
        """
    ):
        if row["new_status"] == "attivo":
            kind = MOVE_REJOINED if row["previous_status"] in ("ex_membro", "bannato") else None
        elif row["previous_status"] == "attivo":
            kind = MOVE_BANNED if row["new_status"] == "bannato" else MOVE_LEFT
        else:
            kind = None
        if kind is not None:
            consider(
                row["id"], row["family_name"], row["main_name"], row["changed_at"][:10], kind, (1, row["history_id"])
            )
    movements = [entry for _, entry in latest.values()]
    movements.sort(key=lambda m: (m["day"], m["id"]), reverse=True)
    return movements[:limit]
