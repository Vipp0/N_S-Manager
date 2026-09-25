import sqlite3

import pytest

from gilda_app.db.database import (
    add_member,
    delete_member,
    get_members,
    get_status_history,
    move_member_status,
    rebuild_status_history,
    reset_database,
    update_member,
    update_status_history_entry,
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


def test_add_member_with_join_date_reflects_in_history(conn):
    member_id = add_member(
        conn, "Rossi", "Mario", "rossi#1234", ["Italy"], STATUS_ATTIVO,
        data_inserimento="2024-01-15", note="amico di Luigi",
    )
    history = get_status_history(conn, member_id)
    assert len(history) == 1
    assert history[0]["changed_at"].startswith("2024-01-15")
    # la nota generale del membro non deve finire nello storico movimenti
    assert history[0]["note"] is None


def test_update_member_syncs_join_history_entry(conn):
    member_id = add_member(conn, "Rossi", "Mario", "rossi#1234", ["Italy"], STATUS_ATTIVO)
    update_member(
        conn, member_id, "Rossi", "Mario", "rossi#1234", ["Italy"],
        data_inserimento="2023-05-01", update_date=True,
    )
    history = get_status_history(conn, member_id)
    assert history[0]["changed_at"].startswith("2023-05-01")


def test_update_status_history_entry_syncs_join_date(conn):
    member_id = add_member(conn, "Rossi", "Mario", "rossi#1234", ["Italy"], STATUS_ATTIVO)
    move_member_status(conn, member_id, STATUS_BANNATO, note="prima nota")

    history = get_status_history(conn, member_id)
    join_entry_id = history[0]["id"]
    ban_entry_id = history[1]["id"]

    update_status_history_entry(conn, join_entry_id, "2022-03-10", None)
    update_status_history_entry(conn, ban_entry_id, "2022-04-01", "nota corretta")

    updated = get_status_history(conn, member_id)
    assert updated[0]["changed_at"].startswith("2022-03-10")
    assert updated[1]["changed_at"].startswith("2022-04-01")
    assert updated[1]["note"] == "nota corretta"

    # correggere la voce di ingresso deve aggiornare anche members.data_inserimento
    member = get_members(conn, STATUS_BANNATO)[0]
    assert member.data_inserimento == "2022-03-10"


def test_rebuild_status_history_replaces_sequence(conn):
    member_id = add_member(conn, "Rossi", "Mario", "rossi#1234", ["Italy"], STATUS_ATTIVO)
    move_member_status(conn, member_id, STATUS_BANNATO, note="voce vecchia da sostituire")

    rebuild_status_history(
        conn,
        member_id,
        [
            {"status": STATUS_ATTIVO, "date": "2020-01-10", "note": None},
            {"status": STATUS_EX_MEMBRO, "date": "2021-06-01", "note": "trasferito"},
            {"status": STATUS_ATTIVO, "date": "2022-02-15", "note": "rientrato"},
        ],
    )

    history = get_status_history(conn, member_id)
    assert len(history) == 3
    assert history[0]["previous_status"] is None
    assert history[0]["new_status"] == STATUS_ATTIVO
    assert history[0]["changed_at"].startswith("2020-01-10")
    assert history[1]["previous_status"] == STATUS_ATTIVO
    assert history[1]["new_status"] == STATUS_EX_MEMBRO
    assert history[2]["previous_status"] == STATUS_EX_MEMBRO
    assert history[2]["new_status"] == STATUS_ATTIVO

    # lo stato corrente e la data di ingresso seguono l'ultimo/primo passaggio ricostruito
    assert get_members(conn, STATUS_BANNATO) == []
    member = get_members(conn, STATUS_ATTIVO)[0]
    assert member.data_inserimento == "2020-01-10"


def test_delete_setting_leaves_no_trace_in_file(tmp_path):
    from gilda_app.db.database import connect, delete_setting, get_setting, set_setting

    path = tmp_path / "t.db"
    connection = connect(path)
    set_setting(connection, "bdoalerts_api_key", "SEGRETO-DA-CANCELLARE-123456")
    delete_setting(connection, "bdoalerts_api_key")
    connection.close()

    assert b"SEGRETO-DA-CANCELLARE" not in path.read_bytes()
    assert get_setting(connect(path), "bdoalerts_api_key") is None


def test_name_history_recorded_on_edit(conn):
    from gilda_app.db.database import get_name_history, old_names_by_member

    member_id = add_member(conn, "Rossi", "Mario", "rossi#1234", [], STATUS_ATTIVO)
    # senza record_name_changes (import) non si registra nulla
    update_member(conn, member_id, "Bianchi", "Mario", "rossi#1234", [])
    assert get_name_history(conn, member_id) == []

    update_member(conn, member_id, "Verdi", "Mario", "rossi#1234", [], record_name_changes=True)
    history = get_name_history(conn, member_id)
    assert [(h["field"], h["old_value"], h["new_value"]) for h in history] == [("family_name", "Bianchi", "Verdi")]
    assert old_names_by_member(conn) == {member_id: ["Bianchi"]}

    # nessuna modifica del nome: nessuna nuova voce
    update_member(conn, member_id, "Verdi", "Mario2", "rossi#1234", [], record_name_changes=True)
    assert len(get_name_history(conn, member_id)) == 1


def test_name_history_manual_crud_and_cascade(conn):
    from gilda_app.db.database import add_name_change, delete_name_change, get_name_history, update_name_change

    member_id = add_member(conn, "Rossi", "", "", [], STATUS_ATTIVO)
    add_name_change(conn, member_id, "family_name", "Vecchio", "Rossi", date="2023-05-01")
    entry = get_name_history(conn, member_id)[0]
    assert entry["changed_at"].startswith("2023-05-01")
    update_name_change(conn, entry["id"], "Altro", "Rossi", "2023-06-02")
    entry = get_name_history(conn, member_id)[0]
    assert entry["old_value"] == "Altro" and entry["changed_at"].startswith("2023-06-02")
    delete_name_change(conn, entry["id"])
    assert get_name_history(conn, member_id) == []

    add_name_change(conn, member_id, "family_name", "X", "Rossi")
    delete_member(conn, member_id)
    assert conn.execute("SELECT COUNT(*) FROM name_history").fetchone()[0] == 0


def test_rebuild_history_with_unknown_dates_and_repeated_status(conn):
    member_id = add_member(conn, "Rossi", "", "", [], STATUS_ATTIVO)
    rebuild_status_history(
        conn,
        member_id,
        [
            {"status": STATUS_ATTIVO, "date": "2020-01-10", "note": None},
            {"status": STATUS_ATTIVO, "date": None, "note": "manca un passaggio"},
            {"status": STATUS_EX_MEMBRO, "date": None, "note": None},
            {"status": STATUS_ATTIVO, "date": "2022-02-15", "note": None},
        ],
    )
    history = get_status_history(conn, member_id)
    assert [h["new_status"] for h in history] == [STATUS_ATTIVO, STATUS_ATTIVO, STATUS_EX_MEMBRO, STATUS_ATTIVO]
    assert [h["changed_at"] is None for h in history] == [False, True, True, False]
    assert history[1]["previous_status"] == STATUS_ATTIVO  # catena mantenuta anche con status ripetuto
    member = get_members(conn, STATUS_ATTIVO)[0]
    assert member.data_inserimento == "2020-01-10"


def test_unknown_first_date_clears_join_date_and_entry_date_can_be_cleared(conn):
    member_id = add_member(conn, "Rossi", "", "", [], STATUS_ATTIVO, data_inserimento="2021-01-01")
    rebuild_status_history(conn, member_id, [{"status": STATUS_ATTIVO, "date": None, "note": None}])
    assert get_members(conn, STATUS_ATTIVO)[0].data_inserimento is None

    entry_id = get_status_history(conn, member_id)[0]["id"]
    update_status_history_entry(conn, entry_id, "2019-05-05", None)
    assert get_members(conn, STATUS_ATTIVO)[0].data_inserimento == "2019-05-05"
    update_status_history_entry(conn, entry_id, None, None)
    assert get_status_history(conn, member_id)[0]["changed_at"] is None
    assert get_members(conn, STATUS_ATTIVO)[0].data_inserimento is None


def test_migration_8_keeps_existing_history():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    from gilda_app.db import migrations

    connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    for upgrade in migrations.MIGRATIONS[:7]:
        upgrade(connection)
    connection.execute("INSERT INTO schema_version (version) VALUES (7)")
    connection.execute(
        "INSERT INTO members (family_name, status) VALUES ('Rossi', 'attivo')"
    )
    connection.execute(
        "INSERT INTO status_history (member_id, previous_status, new_status, changed_at) "
        "VALUES (1, NULL, 'attivo', '2020-01-01 00:00:00')"
    )
    connection.commit()
    migrate(connection)
    row = connection.execute("SELECT * FROM status_history").fetchone()
    assert row["changed_at"] == "2020-01-01 00:00:00" and row["id"] == 1
    connection.execute("INSERT INTO status_history (member_id, new_status, changed_at) VALUES (1, 'ex_membro', NULL)")
    connection.close()
