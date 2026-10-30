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


# -- grafico della copertina ---------------------------------------------------------------------------------
TENURE_BUCKETS = ("lt3", "3_6", "6_12", "1_2", "gt2")  # fasce di anzianità; "nodate" è a parte
TENURE_LIMITS_DAYS = (91, 183, 365, 730)  # sotto 3 mesi, 6 mesi, 1 anno, 2 anni


def tracking_start(conn: sqlite3.Connection) -> date | None:
    """Da quando il programma registra i movimenti: il giorno del primo inserimento di un membro. Le uscite di
    prima non si possono sapere, quindi non vanno mostrate come zero."""
    first = conn.execute("SELECT MIN(created_at) FROM members").fetchone()[0]
    return date.fromisoformat(first[:10]) if first else None


def _month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def last_months(today: date, months: int) -> list[str]:
    """Gli ultimi `months` mesi (yyyy-mm), dal più vecchio al mese di `today`."""
    keys = []
    year, month = today.year, today.month
    for _ in range(months):
        keys.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return keys[::-1]


def monthly_turnover(conn: sqlite3.Connection, today: date, months: int = 12) -> list[dict]:
    """Per ognuno degli ultimi `months` mesi: ingressi (data di ingresso registrata e rientri) e uscite (da membro
    attuale a ex membro o bannato). Le uscite dei mesi prima che il programma cominciasse a registrarle sono
    None (non si sanno), non 0. Dict con month, joins, exits."""
    keys = last_months(today, months)
    joins = dict.fromkeys(keys, 0)
    exits = dict.fromkeys(keys, 0)
    for (stamp,) in conn.execute("SELECT data_inserimento FROM members WHERE data_inserimento IS NOT NULL"):
        if stamp[:7] in joins:
            joins[stamp[:7]] += 1
    for previous, new, stamp in conn.execute(
        "SELECT previous_status, new_status, changed_at FROM status_history "
        "WHERE previous_status IS NOT NULL AND changed_at IS NOT NULL"
    ):
        key = stamp[:7]
        if key not in joins:
            continue
        if new == STATUS_ATTIVO:
            joins[key] += 1
        elif previous == STATUS_ATTIVO:
            exits[key] += 1
    start = tracking_start(conn)
    first_known = _month_key(start) if start else keys[-1]
    return [
        {"month": key, "joins": joins[key], "exits": exits[key] if key >= first_known else None} for key in keys
    ]


def membership_trend(conn: sqlite3.Connection, today: date, months: int = 12) -> list[tuple[str, int | None]]:
    """Membri attuali a fine di ognuno degli ultimi `months` mesi (l'ultimo è il numero di oggi), ricostruiti
    all'indietro dai movimenti. Dove le uscite non sono registrate la ricostruzione non è affidabile: None."""
    turnover = monthly_turnover(conn, today, months)
    current = conn.execute("SELECT COUNT(*) FROM members WHERE status = ?", (STATUS_ATTIVO,)).fetchone()[0]
    series: list[tuple[str, int | None]] = []
    active: int | None = current
    for entry in reversed(turnover):
        series.append((entry["month"], active))
        if active is not None:
            # il mese prima: oggi meno chi è entrato nel mese, più chi è uscito
            active = active - entry["joins"] + entry["exits"] if entry["exits"] is not None else None
    return series[::-1]


def tenure_distribution(conn: sqlite3.Connection, today: date) -> dict[str, int]:
    """Membri attuali per fascia di anzianità (dalla data di ingresso); "nodate" per chi non ce l'ha."""
    result = dict.fromkeys(TENURE_BUCKETS, 0)
    result["nodate"] = 0
    for (stamp,) in conn.execute("SELECT data_inserimento FROM members WHERE status = ?", (STATUS_ATTIVO,)):
        try:
            days = (today - date.fromisoformat(stamp[:10])).days if stamp else None
        except ValueError:
            days = None
        if days is None:
            result["nodate"] += 1
            continue
        bucket = next((name for name, limit in zip(TENURE_BUCKETS, TENURE_LIMITS_DAYS) if days < limit), "gt2")
        result[bucket] += 1
    return result
