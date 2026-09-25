"""Query statistiche derivate da members + status_history."""
import sqlite3
from collections import defaultdict
from datetime import date, datetime

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
        "SELECT previous_status, new_status, changed_at FROM status_history ORDER BY changed_at, id"
    ).fetchall()

    monthly_delta: dict[str, int] = defaultdict(int)
    for row in rows:
        if row["changed_at"] is None:  # data sconosciuta: non si sa in che mese collocarla
            continue
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
        "ORDER BY member_id, id"
    ).fetchall()

    entered_at: dict[int, str] = {}
    durations = []
    for row in rows:
        member_id = row["member_id"]
        if row["changed_at"] is None:
            # Data sconosciuta: la permanenza che la coinvolge non è calcolabile.
            entered_at.pop(member_id, None)
            continue
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


def dated_members_count(conn: sqlite3.Connection, status: str = STATUS_ATTIVO) -> int:
    """Quanti membri con questo status hanno una data di ingresso realmente nota
    (non quella, uguale per tutti, del giorno dell'import iniziale)."""
    return conn.execute(
        "SELECT COUNT(*) FROM members WHERE status = ? AND data_inserimento IS NOT NULL",
        (status,),
    ).fetchone()[0]


def hall_of_fame(conn: sqlite3.Connection, limit: int = 10) -> list[sqlite3.Row]:
    """Membri attuali ordinati per anzianità, basata sulla data di ingresso nota
    (members.data_inserimento), non sullo storico movimenti: per i membri importati
    in blocco quest'ultimo coincide col giorno dell'import per tutti, quindi non
    direbbe nulla sull'anzianità reale."""
    return conn.execute(
        """
        SELECT family_name AS family_name, main_name AS main_name, data_inserimento AS since
        FROM members
        WHERE status = ? AND data_inserimento IS NOT NULL
        ORDER BY data_inserimento ASC
        LIMIT ?
        """,
        (STATUS_ATTIVO, limit),
    ).fetchall()


def _anniversary_in_year(joined: date, year: int) -> date:
    try:
        return joined.replace(year=year)
    except ValueError:  # 29 febbraio in un anno non bisestile
        return date(year, 2, 28)


def upcoming_anniversaries(
    conn: sqlite3.Connection, today: date, days: int = 30, limit: int = 10
) -> list[tuple[date, str, str, int]]:
    """(data, family_name, main_name, anni) dei prossimi anniversari di ingresso dei
    membri attuali con data di ingresso nota, da oggi a `days` giorni. Solo dal primo
    anno compiuto in poi."""
    rows = conn.execute(
        "SELECT family_name, main_name, data_inserimento FROM members "
        "WHERE status = ? AND data_inserimento IS NOT NULL",
        (STATUS_ATTIVO,),
    ).fetchall()
    result = []
    for row in rows:
        try:
            joined = date.fromisoformat(row["data_inserimento"][:10])
        except ValueError:
            continue
        for year in (today.year, today.year + 1):
            anniversary = _anniversary_in_year(joined, year)
            if anniversary >= today:
                break
        years = anniversary.year - joined.year
        if years >= 1 and (anniversary - today).days <= days:
            result.append((anniversary, row["family_name"], row["main_name"] or "", years))
    result.sort(key=lambda item: (item[0], item[1].lower()))
    return result[:limit]


def upcoming_birthdays(
    conn: sqlite3.Connection, today: date, days: int = 14, limit: int = 8
) -> list[tuple[date, str, str, int | None]]:
    """(data, family_name, main_name, età che compie o None) dei compleanni dei membri
    attuali da oggi ai prossimi `days` giorni, in ordine di data."""
    from gilda_app.utils.birthday import next_birthday

    rows = conn.execute(
        "SELECT family_name, main_name, birthday FROM members WHERE status = ? AND birthday IS NOT NULL",
        (STATUS_ATTIVO,),
    ).fetchall()
    result = []
    for row in rows:
        upcoming = next_birthday(row["birthday"], today)
        if upcoming is not None and (upcoming[0] - today).days <= days:
            result.append((upcoming[0], row["family_name"], row["main_name"] or "", upcoming[1]))
    result.sort(key=lambda item: (item[0], item[1].lower()))
    return result[:limit]
