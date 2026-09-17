import sqlite3

import pytest

from gilda_app.db.database import add_member, move_member_status
from gilda_app.db.migrations import migrate
from gilda_app.db.stats import (
    active_members_trend,
    avg_tenure_days,
    counts_by_status,
    nation_distribution,
    rejoin_rate,
    top_rejoiners,
)
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


def _backdate(conn, member_id: int, iso_datetime: str) -> None:
    conn.execute(
        "UPDATE status_history SET changed_at = ? WHERE member_id = ? "
        "AND id = (SELECT MAX(id) FROM status_history WHERE member_id = ?)",
        (iso_datetime, member_id, member_id),
    )
    conn.commit()


def test_counts_and_nation_distribution(conn):
    a = add_member(conn, "Rossi", "Mario", "d1", ["Italy"], STATUS_ATTIVO)
    add_member(conn, "Bianchi", "Luigi", "d2", ["Italy", "France"], STATUS_ATTIVO)
    add_member(conn, "Verdi", "Franco", "d3", ["Germany"], STATUS_EX_MEMBRO)

    counts = counts_by_status(conn)
    assert counts[STATUS_ATTIVO] == 2
    assert counts[STATUS_EX_MEMBRO] == 1
    assert counts["totale_storico"] == 3

    dist = {row["nation"]: row["cnt"] for row in nation_distribution(conn, STATUS_ATTIVO)}
    assert dist == {"Italy": 2, "France": 1}


def test_rejoin_rate_and_top_rejoiners(conn):
    m1 = add_member(conn, "Rossi", "Mario", "d1", ["Italy"], STATUS_ATTIVO)
    m2 = add_member(conn, "Bianchi", "Luigi", "d2", ["Italy"], STATUS_ATTIVO)
    add_member(conn, "Verdi", "Franco", "d3", ["Italy"], STATUS_ATTIVO)

    move_member_status(conn, m1, STATUS_EX_MEMBRO)
    move_member_status(conn, m1, STATUS_ATTIVO)
    move_member_status(conn, m2, STATUS_EX_MEMBRO)

    assert rejoin_rate(conn) == pytest.approx(50.0)

    rejoiners = top_rejoiners(conn)
    assert len(rejoiners) == 1
    assert rejoiners[0]["family_name"] == "Rossi"
    assert rejoiners[0]["rejoin_count"] == 1


def test_avg_tenure_and_trend(conn):
    m1 = add_member(conn, "Rossi", "Mario", "d1", ["Italy"], STATUS_ATTIVO)
    _backdate(conn, m1, "2026-01-01 00:00:00")

    move_member_status(conn, m1, STATUS_BANNATO)
    _backdate(conn, m1, "2026-01-11 00:00:00")

    avg = avg_tenure_days(conn)
    assert avg == pytest.approx(10.0)

    trend = active_members_trend(conn)
    assert trend == [("2026-01", 0)]
