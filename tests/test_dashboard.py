import sqlite3
from datetime import date

import pytest

from gilda_app.db.calendar_events import add_event
from gilda_app.db.dashboard import joined_recently, recent_transitions, transitions_to, upcoming_agenda
from gilda_app.db.database import add_member, move_member_status
from gilda_app.db.holidays import store_holidays
from gilda_app.db.migrations import migrate
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


def test_transitions_ignore_initial_joins(conn):
    a = add_member(conn, "Rossi", "", "", [], STATUS_ATTIVO)
    add_member(conn, "Bianchi", "", "", [], STATUS_ATTIVO)
    move_member_status(conn, a, STATUS_EX_MEMBRO)
    rows = recent_transitions(conn)
    assert [r["family_name"] for r in rows] == ["Rossi"]
    assert transitions_to(conn, STATUS_EX_MEMBRO) == 1
    assert transitions_to(conn, STATUS_BANNATO) == 0


def test_joined_recently_uses_join_date(conn):
    add_member(conn, "Nuovo", "", "", [], STATUS_ATTIVO, data_inserimento=date.today().isoformat())
    add_member(conn, "Vecchio", "", "", [], STATUS_ATTIVO, data_inserimento="2020-01-01")
    add_member(conn, "SenzaData", "", "", [], STATUS_ATTIVO)
    assert joined_recently(conn) == 1


def test_upcoming_agenda_merges_events_and_holidays(conn):
    add_event(conn, start_date="2026-09-25", title="GvG", color="#0f6cbd")
    add_event(conn, start_date="2026-10-20", title="Lontano", color="#0f6cbd")
    store_holidays(conn, [(date(2026, 9, 25), "Chuseok"), (date(2026, 9, 24), "Chuseok Holiday")])
    agenda = upcoming_agenda(conn, date(2026, 9, 24))
    assert agenda == [
        (date(2026, 9, 24), "Chuseok Holiday", True),
        (date(2026, 9, 25), "GvG", False),
        (date(2026, 9, 25), "Chuseok", True),
    ]


def test_history_row_colors():
    from gilda_app.ui.member_dialog import (
        HISTORY_COLOR_BAN, HISTORY_COLOR_EX, HISTORY_COLOR_JOIN, HISTORY_COLOR_REJOIN, history_row_color,
    )

    def row(prev, new):
        return {"previous_status": prev, "new_status": new}

    assert history_row_color(row(None, STATUS_ATTIVO)) == HISTORY_COLOR_JOIN
    assert history_row_color(row(STATUS_ATTIVO, STATUS_EX_MEMBRO)) == HISTORY_COLOR_EX
    assert history_row_color(row(STATUS_ATTIVO, STATUS_BANNATO)) == HISTORY_COLOR_BAN
    assert history_row_color(row(STATUS_EX_MEMBRO, STATUS_ATTIVO)) == HISTORY_COLOR_REJOIN


def test_recent_joins_and_anniversaries(conn):
    from gilda_app.db.dashboard import recent_joins
    from gilda_app.db.stats import upcoming_anniversaries

    add_member(conn, "Vecchio", "V", "", [], STATUS_ATTIVO, data_inserimento="2023-10-05")
    add_member(conn, "Nuovo", "N", "", [], STATUS_ATTIVO, data_inserimento="2026-09-20")
    add_member(conn, "Bisestile", "B", "", [], STATUS_ATTIVO, data_inserimento="2024-02-29")
    add_member(conn, "Senza", "S", "", [], STATUS_ATTIVO)
    add_member(conn, "Ex", "E", "", [], STATUS_EX_MEMBRO, data_inserimento="2020-10-01")

    assert [r["family_name"] for r in recent_joins(conn, 2)] == ["Nuovo", "Bisestile"]

    today = date(2026, 9, 24)
    result = upcoming_anniversaries(conn, today, days=30)
    assert result == [(date(2026, 10, 5), "Vecchio", "V", 3)]
    # 29 febbraio -> 28 febbraio negli anni non bisestili; il "Nuovo" (0 anni) non compare
    result = upcoming_anniversaries(conn, date(2027, 2, 20), days=30)
    assert result == [(date(2027, 2, 28), "Bisestile", "B", 3)]
