import json
import sqlite3
from datetime import date, datetime, timedelta

import pytest

from gilda_app.db import event_log, migrations
from gilda_app.db.dashboard import joined_recently, recent_joins
from gilda_app.db.database import (
    add_member,
    add_name_change,
    delete_member,
    move_member_status,
    rebuild_status_history,
    update_member,
    update_name_change,
    update_status_history_entry,
)
from gilda_app.db.migrations import migrate
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    migrate(connection)
    yield connection
    connection.close()


def kinds(conn):
    return [(e["kind"], e["from_status"], e["to_status"]) for e in reversed(event_log.get_events(conn))]


def test_adding_a_member_is_logged_green_only_for_current_members(conn):
    add_member(conn, "Rossi", "", "", [], STATUS_ATTIVO)
    add_member(conn, "Verdi", "", "", [], STATUS_EX_MEMBRO)
    first, second = reversed(event_log.get_events(conn))
    assert (first["member_name"], event_log.tone(first)) == ("Rossi", event_log.TONE_GOOD)
    assert event_log.tone(second) == event_log.TONE_NEUTRAL  # un ex membro registrato non è un ingresso


def test_the_join_date_is_noted_only_when_it_is_not_today(conn):
    add_member(conn, "Oggi", "", "", [], STATUS_ATTIVO, data_inserimento=date.today().isoformat())
    add_member(conn, "Prima", "", "", [], STATUS_ATTIVO, data_inserimento="2026-09-01")
    today_row, earlier_row = reversed(event_log.get_events(conn))
    assert event_log.event_detail(today_row) == {}
    assert event_log.event_detail(earlier_row) == {"joined": "2026-09-01"}


def test_status_changes_are_green_for_entering_and_red_for_leaving(conn):
    member = add_member(conn, "Rossi", "", "", [], STATUS_ATTIVO)
    move_member_status(conn, member, STATUS_EX_MEMBRO)
    move_member_status(conn, member, STATUS_ATTIVO)
    move_member_status(conn, member, STATUS_BANNATO, note="spam")
    move_member_status(conn, member, STATUS_EX_MEMBRO)  # da bannato a ex membro: né entra né esce
    events = list(reversed(event_log.get_events(conn)))[1:]
    assert [event_log.tone(e) for e in events] == [
        event_log.TONE_BAD, event_log.TONE_GOOD, event_log.TONE_BAD, event_log.TONE_NEUTRAL
    ]
    assert event_log.event_detail(events[2]) == {"note": "spam"}


def test_returning_from_banned_is_green_too(conn):
    member = add_member(conn, "Rossi", "", "", [], STATUS_BANNATO)
    move_member_status(conn, member, STATUS_ATTIVO)
    assert event_log.tone(event_log.get_events(conn)[0]) == event_log.TONE_GOOD


def test_a_family_name_change_is_its_own_event_and_other_fields_are_grouped(conn):
    member = add_member(conn, "Rossi", "Mario", "mario#1", ["Italia"], STATUS_ATTIVO)
    update_member(
        conn, member, "Rossi2", "Marione", "mario#1", ["Italia", "Francia"], "una nota", record_name_changes=True
    )
    events = list(reversed(event_log.get_events(conn)))[1:]
    assert [e["kind"] for e in events] == ["name", "edit"]
    assert event_log.event_detail(events[0])["changes"] == [{"field": "family_name", "old": "Rossi", "new": "Rossi2"}]
    fields = {c["field"]: (c["old"], c["new"]) for c in event_log.event_detail(events[1])["changes"]}
    assert fields == {
        "main_name": ("Mario", "Marione"),
        "nations": ("Italia", "Italia, Francia"),
        "note": ("", "una nota"),
    }
    assert events[1]["member_name"] == "Rossi2"


def test_a_save_without_changes_writes_nothing(conn):
    member = add_member(conn, "Rossi", "Mario", "", ["Italia"], STATUS_ATTIVO)
    before = len(event_log.get_events(conn))
    update_member(conn, member, "Rossi", "Mario", "", ["Italia"], None)
    assert len(event_log.get_events(conn)) == before


def test_the_import_writes_no_per_row_events(conn):
    member = add_member(conn, "Rossi", "", "", [], STATUS_ATTIVO, log=False)
    update_member(conn, member, "Rossi", "Nuovo", "", [], None, log=False)
    assert event_log.get_events(conn) == []


def test_a_deleted_member_stays_in_the_log_with_the_name(conn):
    member = add_member(conn, "Rossi", "", "", [], STATUS_EX_MEMBRO)
    delete_member(conn, member)
    last = event_log.get_events(conn)[0]
    assert (last["kind"], last["member_name"], last["from_status"]) == ("delete", "Rossi", STATUS_EX_MEMBRO)
    assert conn.execute("SELECT COUNT(*) FROM event_log WHERE member_name = 'Rossi'").fetchone()[0] == 2


def test_history_corrections_are_logged(conn):
    member = add_member(conn, "Rossi", "", "", [], STATUS_ATTIVO)
    entry = conn.execute("SELECT id FROM status_history WHERE member_id = ?", (member,)).fetchone()["id"]
    update_status_history_entry(conn, entry, "2026-01-01", None)
    rebuild_status_history(conn, member, [{"status": STATUS_ATTIVO, "date": "2026-01-01", "note": None}])
    add_name_change(conn, member, "family_name", "Vecchio", "Rossi", "2026-02-02", log=True)
    row = conn.execute("SELECT id FROM name_history").fetchone()
    update_name_change(conn, row["id"], "Vecchio", "Rossi", "2026-02-03")
    whats = [event_log.event_detail(e)["what"] for e in reversed(event_log.get_events(conn)) if e["kind"] == "history"]
    assert whats == ["status_entry", "status_rebuilt", "name_added", "name_edited"]


def test_editing_a_member_does_not_log_the_name_history_twice(conn):
    member = add_member(conn, "Rossi", "", "", [], STATUS_ATTIVO)
    update_member(conn, member, "Bianchi", "", "", [], None, record_name_changes=True)
    assert [e["kind"] for e in reversed(event_log.get_events(conn))] == ["added", "name"]


def test_events_are_newest_first_and_the_limit_applies(conn):
    for name in ("A", "B", "C"):
        add_member(conn, name, "", "", [], STATUS_ATTIVO)
        conn.execute("UPDATE event_log SET at = ? WHERE member_name = ?", (f"2026-10-0{ord(name) - 64} 10:00:00", name))
    assert [e["member_name"] for e in event_log.get_events(conn)] == ["C", "B", "A"]
    assert [e["member_name"] for e in event_log.get_events(conn, limit=2)] == ["C", "B"]


# -- migrazione: eventi recuperati dallo storico esistente ----------------------------------------
def _db_before_the_log():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    for upgrade in migrations.MIGRATIONS[:8]:
        upgrade(connection)
    return connection


def test_the_migration_recovers_every_dated_event_but_not_bulk_imports():
    c = _db_before_the_log()
    today = date.today()
    recent = (today - timedelta(days=10)).isoformat()
    old = "2024-03-05"
    names = ("Recente", "Vecchio", "Datato", "Rinominato", "Manuale", "Import1", "Import2", "Import3")
    for i, name in enumerate(names, start=1):
        c.execute("INSERT INTO members (id, family_name, status) VALUES (?, ?, 'attivo')", (i, name))
    insert = "INSERT INTO status_history (member_id, previous_status, new_status, changed_at) VALUES (?, ?, ?, ?)"
    c.execute(insert, (1, "attivo", "ex_membro", f"{recent} 08:30:00"))  # passaggio recente, ora UTC
    c.execute(insert, (2, "attivo", "ex_membro", f"{old} 08:30:00"))  # vecchio: si recupera lo stesso
    c.execute(insert, (3, None, "attivo", f"{recent} 00:00:00"))  # ingresso con data certa
    c.execute(insert, (5, None, "attivo", f"{recent} 17:45:10"))  # aggiunto a mano: un solo ingresso in quel secondo
    for member in (6, 7, 8):  # tre "ingressi" nello stesso istante: un import in blocco, non sono eventi
        c.execute(insert, (member, None, "attivo", f"{recent} 11:11:11"))
    c.execute(
        "INSERT INTO name_history (member_id, field, old_value, new_value, changed_at) VALUES (4, 'family_name', 'A', 'B', ?)",
        (f"{old} 00:00:00",),
    )
    migrations._upgrade_9(c)
    rows = {r["member_name"]: r for r in c.execute("SELECT * FROM event_log")}
    assert set(rows) == {"Recente", "Vecchio", "Datato", "Rinominato", "Manuale"}
    assert rows["Vecchio"]["at"][:10] in (old, "2024-03-05")
    assert rows["Manuale"]["kind"] == "added"
    assert (rows["Recente"]["kind"], rows["Recente"]["from_status"], rows["Recente"]["to_status"]) == (
        "status", "attivo", "ex_membro"
    )
    assert rows["Recente"]["at"][:10] in (recent, (today - timedelta(days=9)).isoformat())  # UTC -> ora locale
    assert (rows["Datato"]["kind"], rows["Datato"]["at"]) == ("added", f"{recent} 00:00:00")  # data senza ora: invariata
    assert json.loads(rows["Rinominato"]["detail"])["changes"][0]["new"] == "B"


def test_the_migration_is_part_of_the_schema(conn):
    assert conn.execute("SELECT version FROM schema_version").fetchone()[0] == len(migrations.MIGRATIONS)
    assert conn.execute("SELECT COUNT(*) FROM event_log").fetchone()[0] == 0


# -- dashboard: i rientri sono ingressi -------------------------------------------------------------------
def test_a_member_who_returns_shows_in_the_latest_joins(conn):
    old = add_member(conn, "Rientrato", "R", "", [], STATUS_ATTIVO, data_inserimento="2024-01-01")
    add_member(conn, "Nuovo", "N", "", [], STATUS_ATTIVO, data_inserimento=(date.today() - timedelta(days=5)).isoformat())
    move_member_status(conn, old, STATUS_EX_MEMBRO)
    move_member_status(conn, old, STATUS_ATTIVO)
    joins = recent_joins(conn)
    assert [(j["family_name"], j["rejoined"]) for j in joins] == [("Rientrato", True), ("Nuovo", False)]
    assert joins[0]["joined_on"] == date.today().isoformat() or joins[0]["joined_on"] == datetime.utcnow().date().isoformat()


def test_a_member_who_left_again_is_not_in_the_latest_joins(conn):
    member = add_member(conn, "Uscito", "", "", [], STATUS_ATTIVO, data_inserimento="2024-01-01")
    move_member_status(conn, member, STATUS_EX_MEMBRO)
    move_member_status(conn, member, STATUS_ATTIVO)
    move_member_status(conn, member, STATUS_EX_MEMBRO)
    assert recent_joins(conn) == []


def test_a_rejoin_without_a_registered_join_date_still_counts(conn):
    member = add_member(conn, "SenzaData", "", "", [], STATUS_EX_MEMBRO)
    move_member_status(conn, member, STATUS_ATTIVO)
    assert [j["family_name"] for j in recent_joins(conn)] == ["SenzaData"]


def test_the_thirty_day_join_count_includes_returns(conn):
    first = add_member(conn, "Nuovo", "", "", [], STATUS_ATTIVO, data_inserimento=date.today().isoformat())
    ex = add_member(conn, "Ex", "", "", [], STATUS_EX_MEMBRO)
    assert joined_recently(conn) == 1
    move_member_status(conn, ex, STATUS_ATTIVO)
    assert joined_recently(conn) == 2
    assert first


def test_an_old_return_is_not_in_the_recent_count(conn):
    member = add_member(conn, "Vecchio", "", "", [], STATUS_EX_MEMBRO)
    move_member_status(conn, member, STATUS_ATTIVO)
    conn.execute("UPDATE status_history SET changed_at = '2025-01-01 10:00:00' WHERE previous_status IS NOT NULL")
    assert joined_recently(conn) == 0
    assert recent_joins(conn)[0]["joined_on"] == "2025-01-01"
