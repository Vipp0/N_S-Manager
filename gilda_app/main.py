import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from qfluentwidgets import MessageBox

from gilda_app.db.backup import backup_database
from gilda_app.db.database import connect
from gilda_app.importer.excel_import import run_initial_import
from gilda_app.ui.main_window import MainWindow
from gilda_app.utils.paths import db_path


def _maybe_run_initial_import(conn, db_file: Path, parent) -> None:
    """Se il DB è vuoto, propone di importare il file Excel esistente."""
    row = conn.execute("SELECT COUNT(*) FROM members").fetchone()
    if row[0] > 0:
        return

    default_xlsx = db_file.parent / "List 2026.xlsx"
    if default_xlsx.exists():
        box = MessageBox(
            "Importazione iniziale",
            f'Il database è vuoto. Importare i dati da "{default_xlsx.name}" trovato nella cartella?',
            parent,
        )
        if box.exec():
            backup_database(db_file, "initial_import")
            outcome = run_initial_import(conn, default_xlsx)
            summary = "\n".join(
                f"{r.sheet_name}: {r.imported_rows} righe importate, {r.skipped_blank} scartate"
                for r in outcome["sheet_reports"]
            )
            MessageBox(
                "Import completato",
                f"{summary}\nDuplicati incrociati saltati: {outcome['skipped_duplicate']}",
                parent,
            ).exec()


def main() -> None:
    app = QApplication(sys.argv)

    db_file = db_path()
    conn = connect(db_file)

    window = MainWindow(conn, db_file)
    _maybe_run_initial_import(conn, db_file, window)
    window.refresh_all()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
