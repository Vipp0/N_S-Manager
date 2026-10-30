"""Dati del grafico della copertina (ingressi e uscite, andamento, anzianità) e posti della gilda."""
import sqlite3
from datetime import date

import pytest

from gilda_app.capacity import DEFAULT_GUILD_CAPACITY, GUILD_CAPACITY_SETTING, guild_capacity
from gilda_app.db import dashboard as queries
from gilda_app.db.database import add_member, set_setting
from gilda_app.db.migrations import migrate
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO

TODAY = date(2026, 10, 30)


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


def _history(conn, member_id, previous, new, stamp):
    conn.execute(
        "INSERT INTO status_history (member_id, previous_status, new_status, changed_at) VALUES (?, ?, ?, ?)",
        (member_id, previous, new, stamp),
    )


def _tracking_since(conn, day):
    conn.execute("UPDATE members SET created_at = ?", (f"{day} 09:00:00",))


def test_last_months_runs_from_the_oldest_to_the_current_month_across_the_new_year():
    assert queries.last_months(date(2026, 2, 10), 4) == ["2025-11", "2025-12", "2026-01", "2026-02"]
    assert len(queries.last_months(TODAY, 12)) == 12 and queries.last_months(TODAY, 12)[-1] == "2026-10"


def test_turnover_counts_joins_and_exits_and_leaves_unrecorded_months_empty(conn):
    a = add_member(conn, "A", "", "", [], STATUS_ATTIVO, data_inserimento="2026-09-05")
    b = add_member(conn, "B", "", "", [], STATUS_ATTIVO, data_inserimento="2026-03-01")
    add_member(conn, "SenzaData", "", "", [], STATUS_ATTIVO)  # niente data: non conta come ingresso di nessun mese
    _history(conn, b, STATUS_ATTIVO, STATUS_EX_MEMBRO, "2026-09-20 10:00:00")
    _history(conn, a, STATUS_ATTIVO, STATUS_BANNATO, "2026-10-02 10:00:00")
    _history(conn, b, STATUS_EX_MEMBRO, STATUS_ATTIVO, "2026-10-10 10:00:00")  # rientro: un ingresso
    _tracking_since(conn, "2026-09-01")

    by_month = {e["month"]: e for e in queries.monthly_turnover(conn, TODAY, 12)}
    assert by_month["2026-09"] == {"month": "2026-09", "joins": 1, "exits": 1}
    assert by_month["2026-10"] == {"month": "2026-10", "joins": 1, "exits": 1}
    assert by_month["2026-03"]["joins"] == 1 and by_month["2026-03"]["exits"] is None  # prima: uscite non registrate
    assert by_month["2026-08"]["exits"] is None
    assert queries.tracking_start(conn) == date(2026, 9, 1)


def test_trend_is_rebuilt_backwards_and_empty_where_exits_are_unknown(conn):
    a = add_member(conn, "A", "", "", [], STATUS_ATTIVO, data_inserimento="2026-09-05")
    add_member(conn, "B", "", "", [], STATUS_ATTIVO, data_inserimento="2026-10-05")
    c = add_member(conn, "C", "", "", [], STATUS_EX_MEMBRO, data_inserimento="2026-01-01")
    _history(conn, c, STATUS_ATTIVO, STATUS_EX_MEMBRO, "2026-09-15 10:00:00")
    _tracking_since(conn, "2026-09-01")
    trend = dict(queries.membership_trend(conn, TODAY, 12))
    assert trend["2026-10"] == 2  # oggi: A e B
    assert trend["2026-09"] == 1  # a fine settembre B non c'era ancora
    assert trend["2026-08"] == 1 - 1 + 1  # A è entrato a settembre; C è uscito a settembre: indietro si aggiunge
    assert trend["2026-07"] is None  # le uscite di agosto non sono registrate: da qui non si sa più
    assert trend["2025-11"] is None


def test_tenure_buckets_and_members_without_a_date(conn):
    add_member(conn, "Nuovo", "", "", [], STATUS_ATTIVO, data_inserimento="2026-10-01")  # meno di 3 mesi
    add_member(conn, "Cinque", "", "", [], STATUS_ATTIVO, data_inserimento="2026-05-20")  # 3-6 mesi
    add_member(conn, "Otto", "", "", [], STATUS_ATTIVO, data_inserimento="2026-02-15")  # 6-12 mesi
    add_member(conn, "Uno", "", "", [], STATUS_ATTIVO, data_inserimento="2025-06-01")  # 1-2 anni
    add_member(conn, "Vecchio", "", "", [], STATUS_ATTIVO, data_inserimento="2021-06-01")  # oltre 2 anni
    add_member(conn, "Ignoto", "", "", [], STATUS_ATTIVO)
    add_member(conn, "Ex", "", "", [], STATUS_EX_MEMBRO, data_inserimento="2020-01-01")  # solo i membri attuali
    assert queries.tenure_distribution(conn, TODAY) == {
        "lt3": 1, "3_6": 1, "6_12": 1, "1_2": 1, "gt2": 1, "nodate": 1,
    }


def test_guild_capacity_defaults_to_100_and_ignores_nonsense(conn):
    assert guild_capacity(conn) == DEFAULT_GUILD_CAPACITY == 100
    set_setting(conn, GUILD_CAPACITY_SETTING, "120")
    assert guild_capacity(conn) == 120
    for bad in ("abc", "0", "-5", "100000", ""):
        set_setting(conn, GUILD_CAPACITY_SETTING, bad)
        assert guild_capacity(conn) == 100, bad
