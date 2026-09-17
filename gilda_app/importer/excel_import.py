"""Import da file Excel a 3 fogli (Members / Old Members / No Rejoin) verso il database."""
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl

from gilda_app.db.database import add_member, find_duplicate, update_member
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO

# (nome foglio, status corrispondente, ha intestazione, salta prima colonna indice)
SHEET_SPECS = [
    ("Members", STATUS_ATTIVO, True, True),
    ("Old Members", STATUS_EX_MEMBRO, False, False),
    ("No Rejoin", STATUS_BANNATO, False, False),
]


@dataclass
class ImportRow:
    family_name: str
    main_name: str
    discord_name: str
    nations: list[str]
    status: str


@dataclass
class SheetReport:
    sheet_name: str
    status: str
    imported_rows: int
    skipped_blank: int


@dataclass
class ImportPreview:
    rows: list[ImportRow]
    sheet_reports: list[SheetReport] = field(default_factory=list)


def split_nations(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = [p.strip() for p in str(raw).split("/") if p.strip()]
    return parts[:2]


def _parse_sheet(ws, has_header: bool, skip_first_col: bool) -> tuple[list[ImportRow], int]:
    rows: list[ImportRow] = []
    skipped = 0
    min_row = 2 if has_header else 1
    offset = 1 if skip_first_col else 0

    for values in ws.iter_rows(min_row=min_row, values_only=True):
        family = values[offset] if len(values) > offset else None
        main = values[offset + 1] if len(values) > offset + 1 else None
        nation_raw = values[offset + 2] if len(values) > offset + 2 else None
        discord = values[offset + 3] if len(values) > offset + 3 else None

        family = str(family).strip() if family else ""
        if not family:
            skipped += 1
            continue

        rows.append(
            ImportRow(
                family_name=family,
                main_name=str(main).strip() if main else "",
                discord_name=str(discord).strip() if discord else "",
                nations=split_nations(nation_raw),
                status="",
            )
        )
    return rows, skipped


def parse_workbook(path: Path) -> ImportPreview:
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    all_rows: list[ImportRow] = []
    reports: list[SheetReport] = []

    for sheet_name, status, has_header, skip_first_col in SHEET_SPECS:
        ws = wb[sheet_name]
        rows, skipped = _parse_sheet(ws, has_header, skip_first_col)
        for row in rows:
            row.status = status
        all_rows.extend(rows)
        reports.append(
            SheetReport(sheet_name=sheet_name, status=status, imported_rows=len(rows), skipped_blank=skipped)
        )

    wb.close()
    return ImportPreview(rows=all_rows, sheet_reports=reports)


def import_row(conn: sqlite3.Connection, row: ImportRow, on_duplicate: str = "skip") -> str:
    """Inserisce una riga nel DB. on_duplicate: 'skip' | 'update' | 'insert'. Ritorna l'esito."""
    existing = find_duplicate(conn, row.family_name, row.main_name)
    if existing is not None:
        if on_duplicate == "skip":
            return "skipped"
        if on_duplicate == "update":
            update_member(conn, existing["id"], row.family_name, row.main_name, row.discord_name, row.nations, existing["note"])
            return "updated"
        # on_duplicate == "insert": inserisce comunque come nuova voce

    add_member(
        conn,
        family_name=row.family_name,
        main_name=row.main_name,
        discord_name=row.discord_name,
        nations=row.nations,
        status=row.status,
        data_inserimento=None,
        note=None,
    )
    return "inserted"


def run_initial_import(conn: sqlite3.Connection, path: Path) -> dict:
    """Import una tantum: ordine Members -> Old Members -> No Rejoin, duplicati incrociati saltati."""
    preview = parse_workbook(path)
    outcome = {"inserted": 0, "skipped_duplicate": 0}
    for row in preview.rows:
        result = import_row(conn, row, on_duplicate="skip")
        if result == "inserted":
            outcome["inserted"] += 1
        elif result == "skipped":
            outcome["skipped_duplicate"] += 1
    outcome["sheet_reports"] = preview.sheet_reports
    return outcome
