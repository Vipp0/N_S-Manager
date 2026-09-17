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
