import sys
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication
from qfluentwidgets import MessageBox

from gilda_app.db.backup import backup_database
from gilda_app.db.database import connect, get_setting
from gilda_app.i18n import DEFAULT_LANGUAGE, set_language, tr
from gilda_app.importer.excel_import import run_initial_import
from gilda_app.ui.main_window import MainWindow
from gilda_app.utils.paths import db_path

APP_FONT_FAMILY = "Segoe UI"
APP_FONT_POINT_SIZE = 11


def _maybe_run_initial_import(conn, db_file: Path, parent) -> None:
    """Se il DB è vuoto, propone di importare il file Excel esistente."""
    row = conn.execute("SELECT COUNT(*) FROM members").fetchone()
    if row[0] > 0:
        return

    default_xlsx = db_file.parent / "List 2026.xlsx"
    if default_xlsx.exists():
        box = MessageBox(
            tr("dialog.initial_import.title"),
            tr("dialog.initial_import.body", filename=default_xlsx.name),
            parent,
        )
        if box.exec():
            backup_database(db_file, "initial_import")
            outcome = run_initial_import(conn, default_xlsx)
            summary = "\n".join(
                tr("import.sheet_line", sheet=r.sheet_name, imported=r.imported_rows, skipped=r.skipped_blank)
                for r in outcome["sheet_reports"]
            )
            summary += tr("import.duplicates_skipped", count=outcome["skipped_duplicate"])
            MessageBox(tr("dialog.initial_import_done.title"), summary, parent).exec()


def main() -> None:
    app = QApplication(sys.argv)
    app.setFont(QFont(APP_FONT_FAMILY, APP_FONT_POINT_SIZE))

    db_file = db_path()
    conn = connect(db_file)
    set_language(get_setting(conn, "language", DEFAULT_LANGUAGE))

    window = MainWindow(conn, db_file)
    _maybe_run_initial_import(conn, db_file, window)
    window.refresh_all()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
