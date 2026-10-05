import sqlite3
from pathlib import Path

import pytest

from gilda_app.db.migrations import migrate
from gilda_app.importer.excel_import import find_intra_file_duplicates, parse_workbook, run_initial_import
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO

XLSX_PATH = Path(__file__).resolve().parent.parent / "List 2026.xlsx"


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


def test_initial_import_counts(conn):
    outcome = run_initial_import(conn, XLSX_PATH)

    counts = {r.status: r.imported_rows for r in outcome["sheet_reports"]}
    assert counts[STATUS_ATTIVO] == 104
    assert counts[STATUS_EX_MEMBRO] == 527
    assert counts[STATUS_BANNATO] == 20

    total_in_db = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
    assert total_in_db == outcome["inserted"]


def test_find_intra_file_duplicates():
    preview = parse_workbook(XLSX_PATH)
    duplicates = find_intra_file_duplicates(preview.rows)

    assert len(duplicates) == 6
    names = {(d.duplicate.family_name, d.duplicate.main_name) for d in duplicates}
    assert ("MorningStarr", "DevilentX") in names

    morningstarr = next(d for d in duplicates if d.duplicate.family_name == "MorningStarr")
    assert morningstarr.fields_differ is True

    smushybois = next(d for d in duplicates if d.duplicate.family_name == "Smushybois")
    assert smushybois.fields_differ is False


def test_double_nation_split(conn):
    run_initial_import(conn, XLSX_PATH)
    row = conn.execute(
        "SELECT id FROM members WHERE family_name = 'Astori'"
    ).fetchone()
    assert row is not None
    nations = [
        r["nation"]
        for r in conn.execute(
            "SELECT nation FROM member_nations WHERE member_id = ? ORDER BY ord", (row["id"],)
        ).fetchall()
    ]
    assert nations == ["Algeria", "Dubai"]


def test_exported_file_can_be_imported_back(conn, tmp_path):
    # "Esporta" scrive l'intestazione in tutti e tre i fogli e nessuna colonna "N.":
    # reimportarlo deve ridare gli stessi membri, senza righe d'intestazione scambiate per
    # persone e senza spostare le colonne (il Main Name finiva nel Family Name).
    from gilda_app.db.database import add_member
    from gilda_app.importer.excel_export import export_workbook

    add_member(conn, "AliceFam", "AliceMain", "alice#1", ["Italy", "Spain"], STATUS_ATTIVO)
    add_member(conn, "BobFam", "BobMain", "bob#2", ["Spain"], STATUS_EX_MEMBRO)
    add_member(conn, "CarlFam", "CarlMain", "carl#3", [], STATUS_BANNATO)
    path = tmp_path / "export.xlsx"
    export_workbook(conn, path)

    preview = parse_workbook(path)
    got = [(r.status, r.family_name, r.main_name, r.nations, r.discord_name) for r in preview.rows]
    assert got == [
        (STATUS_ATTIVO, "AliceFam", "AliceMain", ["Italy", "Spain"], "alice#1"),
        (STATUS_EX_MEMBRO, "BobFam", "BobMain", ["Spain"], "bob#2"),
        (STATUS_BANNATO, "CarlFam", "CarlMain", [], "carl#3"),
    ]
    assert [(r.sheet_name, r.row_number) for r in preview.rows] == [("Members", 2), ("Old Members", 2), ("No Rejoin", 2)]


def test_original_layout_still_read_after_header_detection():
    preview = parse_workbook(XLSX_PATH)
    first_member = preview.rows[0]
    assert (first_member.sheet_name, first_member.family_name, first_member.row_number) == ("Members", "AE_Zekken", 2)
    old = next(r for r in preview.rows if r.sheet_name == "Old Members")
    assert (old.family_name, old.row_number) == ("Wolfie", 1)
