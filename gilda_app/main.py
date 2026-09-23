import sys
import time
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication
from qfluentwidgets import MessageBox

from gilda_app.db.backup import daily_backup_if_needed
from gilda_app.db.database import connect, get_setting
from gilda_app.i18n import DEFAULT_LANGUAGE, set_language, tr
from gilda_app.ui.main_window import MainWindow
from gilda_app.utils.paths import db_path

APP_FONT_FAMILY = "Segoe UI"
APP_FONT_POINT_SIZE = 11


def _maybe_run_initial_import(conn, db_file: Path, parent: MainWindow) -> None:
    """Se il DB è vuoto, propone di importare il file Excel esistente. Usa la stessa
    anteprima (con segnalazione dei doppioni) del menu Impostazioni → Importa, invece
    di un import automatico "alla cieca" con policy fissa."""
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
            parent.run_import(default_xlsx)


def _animate_splash_dots() -> None:
    """Fa scorrere "Loading." / "Loading.." / "Loading..." sulla schermata di avvio,
    prima di chiuderla: senza questa pausa voluta la splash resta a schermo troppo poco
    perché l'animazione si veda. Il modulo pyi_splash esiste solo nell'eseguibile
    costruito: in sviluppo l'import fallisce e non c'è nulla da animare."""
    try:
        import pyi_splash
    except ImportError:
        return
    for _ in range(2):
        for frame in ("Loading.", "Loading..", "Loading..."):
            pyi_splash.update_text(frame)
            time.sleep(0.25)


def _close_splash() -> None:
    """Chiude la schermata di avvio del bootloader (vedi gilda_app.spec). Il modulo
    pyi_splash esiste solo nell'eseguibile costruito: in sviluppo l'import fallisce e
    non c'è nulla da chiudere."""
    try:
        import pyi_splash
    except ImportError:
        return
    pyi_splash.close()


def main() -> None:
    app = QApplication(sys.argv)
    app.setFont(QFont(APP_FONT_FAMILY, APP_FONT_POINT_SIZE))

    db_file = db_path()
    # Prima di connect(): così la copia del giorno precede anche un'eventuale migrazione
    # dello schema fatta da una versione nuova del programma.
    try:
        daily_backup_if_needed(db_file)
    except OSError:
        pass
    conn = connect(db_file)
    set_language(get_setting(conn, "language", DEFAULT_LANGUAGE))

    window = MainWindow(conn, db_file)
    window.refresh_all()
    _animate_splash_dots()
    # Finestra mostrata prima di chiudere lo splash: altrimenti Windows non ha una
    # finestra in primo piano da cui passare il focus e l'app parte in background.
    window.show()
    _close_splash()
    window.raise_()
    window.activateWindow()
    _maybe_run_initial_import(conn, db_file, window)
    window.refresh_all()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
