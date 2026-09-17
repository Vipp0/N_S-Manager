"""Query statistiche derivate da members + status_history."""
import sqlite3
from collections import defaultdict
from datetime import datetime

from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO


def counts_by_status(conn: sqlite3.Connection) -> dict:
    counts = {STATUS_ATTIVO: 0, STATUS_EX_MEMBRO: 0, STATUS_BANNATO: 0}
    for row in conn.execute("SELECT status, COUNT(*) AS cnt FROM members GROUP BY status"):
        counts[row["status"]] = row["cnt"]
    counts["totale_storico"] = conn.execute(
        "SELECT COUNT(DISTINCT member_id) FROM status_history"
    ).fetchone()[0]
    return counts


def nation_distribution(conn: sqlite3.Connection, status: str = STATUS_ATTIVO) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT mn.nation AS nation, COUNT(*) AS cnt
        FROM member_nations mn
        JOIN members m ON m.id = mn.member_id
        WHERE m.status = ?
        GROUP BY mn.nation
        ORDER BY cnt DESC
        """,
        (status,),
    ).fetchall()


def active_members_trend(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    """Andamento mensile cumulativo del numero di membri attivi."""
    rows = conn.execute(
        "SELECT previous_status, new_status, changed_at FROM status_history ORDER BY changed_at"
    ).fetchall()

    monthly_delta: dict[str, int] = defaultdict(int)
    for row in rows:
        month = row["changed_at"][:7]
        was_active = row["previous_status"] == STATUS_ATTIVO
        is_active = row["new_status"] == STATUS_ATTIVO
        if is_active and not was_active:
            monthly_delta[month] += 1
        elif was_active and not is_active:
            monthly_delta[month] -= 1

    trend = []
    cumulative = 0
    for month in sorted(monthly_delta):
        cumulative += monthly_delta[month]
        trend.append((month, cumulative))
    return trend


def avg_tenure_days(conn: sqlite3.Connection) -> float | None:
    """Giorni medi di permanenza da 'attivo' prima di uscire (ex membro o bannato)."""
    rows = conn.execute(
        "SELECT member_id, previous_status, new_status, changed_at FROM status_history "
        "ORDER BY member_id, changed_at"
    ).fetchall()

    entered_at: dict[int, str] = {}
    durations = []
    for row in rows:
        member_id = row["member_id"]
        if row["new_status"] == STATUS_ATTIVO:
            entered_at[member_id] = row["changed_at"]
        elif row["previous_status"] == STATUS_ATTIVO and member_id in entered_at:
            start = datetime.fromisoformat(entered_at[member_id])
            end = datetime.fromisoformat(row["changed_at"])
            durations.append((end - start).days)
            del entered_at[member_id]

    if not durations:
        return None
    return sum(durations) / len(durations)


def rejoin_rate(conn: sqlite3.Connection) -> float:
    ever_ex = conn.execute(
        "SELECT COUNT(DISTINCT member_id) FROM status_history WHERE new_status = ?", (STATUS_EX_MEMBRO,)
    ).fetchone()[0]
    if ever_ex == 0:
        return 0.0
    rejoined = conn.execute(
        "SELECT COUNT(DISTINCT member_id) FROM status_history WHERE previous_status = ? AND new_status = ?",
        (STATUS_EX_MEMBRO, STATUS_ATTIVO),
    ).fetchone()[0]
    return rejoined / ever_ex * 100


def top_rejoiners(conn: sqlite3.Connection, limit: int = 5) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT m.family_name AS family_name, m.main_name AS main_name, COUNT(*) AS rejoin_count
        FROM status_history sh
        JOIN members m ON m.id = sh.member_id
        WHERE sh.previous_status = ? AND sh.new_status = ?
        GROUP BY sh.member_id
        ORDER BY rejoin_count DESC
        LIMIT ?
        """,
        (STATUS_EX_MEMBRO, STATUS_ATTIVO, limit),
    ).fetchall()


def recent_changes(conn: sqlite3.Connection, days: int = 30) -> dict[str, int]:
    rows = conn.execute(
        "SELECT new_status AS new_status, COUNT(*) AS cnt FROM status_history "
        "WHERE changed_at >= datetime('now', ?) GROUP BY new_status",
        (f"-{days} days",),
    ).fetchall()
    return {row["new_status"]: row["cnt"] for row in rows}


def common_ban_reasons(conn: sqlite3.Connection, limit: int = 5) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT note AS note, COUNT(*) AS cnt
        FROM status_history
        WHERE new_status = ? AND note IS NOT NULL AND TRIM(note) != ''
        GROUP BY note
        ORDER BY cnt DESC
        LIMIT ?
        """,
        (STATUS_BANNATO, limit),
    ).fetchall()


def hall_of_fame(conn: sqlite3.Connection, limit: int = 10) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT m.family_name AS family_name, m.main_name AS main_name, MIN(sh.changed_at) AS since
        FROM members m
        JOIN status_history sh ON sh.member_id = m.id
        WHERE m.status = ?
        GROUP BY m.id
        ORDER BY since ASC
        LIMIT ?
        """,
        (STATUS_ATTIVO, limit),
    ).fetchall()
