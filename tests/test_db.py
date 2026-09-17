import sqlite3

import pytest

from gilda_app.db.database import (
    add_member,
    delete_member,
    get_members,
    get_status_history,
    move_member_status,
    reset_database,
    update_member,
)
from gilda_app.db.migrations import migrate
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


def test_add_and_get_member(conn):
    member_id = add_member(conn, "Rossi", "Mario", "rossi#1234", ["Italy"], STATUS_ATTIVO)
    members = get_members(conn, STATUS_ATTIVO)
    assert len(members) == 1
    assert members[0].id == member_id
    assert members[0].nations == ["Italy"]

    history = get_status_history(conn, member_id)
    assert len(history) == 1
    assert history[0]["previous_status"] is None
    assert history[0]["new_status"] == STATUS_ATTIVO


def test_update_member(conn):
    member_id = add_member(conn, "Rossi", "Mario", "rossi#1234", ["Italy"], STATUS_ATTIVO)
    update_member(conn, member_id, "Rossi", "Mario2", "rossi#5678", ["Italy", "France"], "nota test")
    members = get_members(conn, STATUS_ATTIVO)
    assert members[0].main_name == "Mario2"
    assert members[0].nations == ["Italy", "France"]
    assert members[0].note == "nota test"


def test_move_member_status_writes_history(conn):
    member_id = add_member(conn, "Rossi", "Mario", "rossi#1234", ["Italy"], STATUS_ATTIVO)
    move_member_status(conn, member_id, STATUS_BANNATO, note="comportamento tossico")

    assert get_members(conn, STATUS_ATTIVO) == []
    banned = get_members(conn, STATUS_BANNATO)
    assert len(banned) == 1

    history = get_status_history(conn, member_id)
    assert len(history) == 2
    assert history[1]["previous_status"] == STATUS_ATTIVO
    assert history[1]["new_status"] == STATUS_BANNATO
    assert history[1]["note"] == "comportamento tossico"


def test_delete_member_cascades(conn):
    member_id = add_member(conn, "Rossi", "Mario", "rossi#1234", ["Italy"], STATUS_ATTIVO)
    delete_member(conn, member_id)
    assert get_members(conn, STATUS_ATTIVO) == []
    assert conn.execute("SELECT COUNT(*) FROM member_nations").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM status_history").fetchone()[0] == 0


def test_reset_database(conn):
    add_member(conn, "Rossi", "Mario", "rossi#1234", ["Italy"], STATUS_ATTIVO)
    add_member(conn, "Bianchi", "Luigi", "bianchi#1234", ["Italy"], STATUS_EX_MEMBRO)
    reset_database(conn)
    assert get_members(conn, STATUS_ATTIVO) == []
    assert get_members(conn, STATUS_EX_MEMBRO) == []
    assert conn.execute("SELECT COUNT(*) FROM status_history").fetchone()[0] == 0

    new_id = add_member(conn, "Verdi", "Franco", "verdi#1234", ["Italy"], STATUS_ATTIVO)
    assert new_id == 1
