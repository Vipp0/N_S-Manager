import sys
import time
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from gilda_app.db.backup import daily_backup_if_needed
from gilda_app.db.database import connect, get_setting
from gilda_app.i18n import DEFAULT_LANGUAGE, set_language, tr, tr_in
from gilda_app.seasons import MODE_AUTO, SEASON_MODE_SETTING, active_season, greeting_active, read_setting
from gilda_app.ui.seasonal_splash import SeasonalSplash
from gilda_app.ui.update_window import run_apply_mode
from gilda_app.utils.error_log import LOG_NAME, install as install_error_log
from gilda_app.utils.paths import app_dir, db_path
from gilda_app.utils.single_instance import SingleInstance
from gilda_app.utils.updater import APPLY_FLAG, cleanup_leftovers
from gilda_app.version import __version__

if TYPE_CHECKING:  # MainWindow si importa dopo, a schermata di caricamento già mostrata (è la parte lenta)
    from gilda_app.ui.main_window import MainWindow

APP_FONT_FAMILY = "Segoe UI"
APP_FONT_POINT_SIZE = 11
NORMAL_SPLASH_HOLD_SECONDS = 0.6  # quanto resta in vista la schermata normale dell'exe prima della dissolvenza
DOTS_STEP_SECONDS = 0.15  # passo dei puntini di "Loading": più breve, per compensare la pausa qui sopra
BOOTLOADER_SPLASH_TITLE = "tk"  # titolo della finestra della schermata di avvio dell'exe (PyInstaller)


def _maybe_run_initial_import(conn, db_file: Path, parent: "MainWindow") -> None:
    """Se il DB è vuoto, propone di importare il file Excel esistente. Usa la stessa
    anteprima (con segnalazione dei doppioni) del menu Impostazioni → Importa, invece
    di un import automatico "alla cieca" con policy fissa."""
    row = conn.execute("SELECT COUNT(*) FROM members").fetchone()
    if row[0] > 0:
        return
    from qfluentwidgets import MessageBox

    default_xlsx = db_file.parent / "List 2026.xlsx"
    if default_xlsx.exists():
        box = MessageBox(
            tr("dialog.initial_import.title"),
            tr("dialog.initial_import.body", filename=default_xlsx.name),
            parent,
        )
        if box.exec():
            parent.run_import(default_xlsx)


def _start_seasonal_splash(db_file: Path) -> SeasonalSplash | None:
    """Nei periodi di festa mostra la schermata di caricamento a tema, sopra quella normale dell'exe (che la
    copre del tutto e si chiude a fine avvio: chiuderla subito rallenta di diversi secondi tutto il resto
    dell'avvio). Il tema e la lingua si leggono dal database in sola lettura, perché il programma non l'ha
    ancora aperto. Qualunque problema -> None: si prosegue con la schermata normale."""
    try:
        mode = read_setting(db_file, SEASON_MODE_SETTING, MODE_AUTO)
        season = active_season(date.today(), mode)
        if season is None:
            return None
        language = read_setting(db_file, "language", DEFAULT_LANGUAGE)
        # Gli auguri solo nei giorni di festa; negli altri giorni del periodo c'è il tema ma la scritta è quella normale.
        greets = greeting_active(season, date.today(), mode)
        text_key = f"season.loading.{season.key}" if greets else "season.loading.plain"
        splash = SeasonalSplash(season, tr_in(language, text_key))
        if _bootloader_splash_present():
            time.sleep(NORMAL_SPLASH_HOLD_SECONDS)  # solo nell'exe: in sviluppo non c'è nulla da far vedere
        splash.fade_in()  # compare subito, prima del lavoro lungo, in dissolvenza sopra quella dell'exe
        _hide_bootloader_splash()
        return splash
    except Exception:
        return None


def _animate_splash_dots(splash: SeasonalSplash | None = None) -> None:
    """Fa scorrere "Loading." / "Loading.." / "Loading..." sulla schermata di avvio,
    prima di chiuderla: senza questa pausa voluta la splash resta a schermo troppo poco
    perché l'animazione si veda. Il modulo pyi_splash esiste solo nell'eseguibile
    costruito: in sviluppo l'import fallisce e non c'è nulla da animare. Con la schermata
    stagionale i puntini si animano su quella."""
    if splash is not None:
        for _ in range(2):
            for dots in (1, 2, 3):
                splash.set_dots(dots)
                time.sleep(DOTS_STEP_SECONDS)
        return
    try:
        import pyi_splash
    except ImportError:
        return
    for _ in range(2):
        for frame in ("Loading.", "Loading..", "Loading..."):
            pyi_splash.update_text(frame)
            time.sleep(0.25)


def _hide_bootloader_splash() -> None:
    """Nasconde (senza chiuderla) la schermata dell'exe, che altrimenti resta sopra quella stagionale: la sua
    finestra, un "tk" a tutto schermo del bootloader, è sempre in primo piano. Chiuderla qui con
    pyi_splash.close() rallenta di diversi secondi tutto il resto dell'avvio, quindi si chiude a fine avvio.
    Solo Windows; in sviluppo non c'è nulla da nascondere. Un problema qualsiasi non deve fermare l'avvio."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        pid = ctypes.windll.kernel32.GetCurrentProcessId()
        enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def hide_if_splash(hwnd, _lparam):
            window_pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
            title = ctypes.create_unicode_buffer(8)
            user32.GetWindowTextW(hwnd, title, len(title))
            if window_pid.value == pid and title.value == BOOTLOADER_SPLASH_TITLE:
                user32.ShowWindow(hwnd, 0)  # SW_HIDE
            return True

        user32.EnumWindows(enum_proc(hide_if_splash), 0)
    except Exception:
        pass


def _bootloader_splash_present() -> bool:
    try:
        import pyi_splash  # noqa: F401
    except ImportError:
        return False
    return True


def _close_splash() -> None:
    """Chiude la schermata di avvio del bootloader (vedi gilda_app.spec). Il modulo
    pyi_splash esiste solo nell'eseguibile costruito: in sviluppo l'import fallisce e
    non c'è nulla da chiudere."""
    try:
        import pyi_splash
    except ImportError:
        return
    pyi_splash.close()


def _bring_to_front(window: "MainWindow") -> None:
    """Una seconda copia è stata lanciata: la finestra già aperta torna in primo piano. Se è
    nascosta (aggiornamento in corso) non la si tocca."""
    if not window.isVisible():
        return
    if window.isMinimized():
        window.showNormal()
    window.raise_()
    window.activateWindow()


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == APPLY_FLAG:
        sys.exit(run_apply_mode(sys.argv[2:], _close_splash))

    install_error_log(app_dir() / LOG_NAME, __version__)
    app = QApplication(sys.argv)
    app.setFont(QFont(APP_FONT_FAMILY, APP_FONT_POINT_SIZE))

    db_file = db_path()
    # Prima di toccare il database: se il programma è già aperto, lo si porta in primo
    # piano e questa copia si chiude, senza backup né migrazioni.
    instance = SingleInstance(db_file)
    if not instance.acquire():
        _close_splash()
        sys.exit(0)
    # Nei periodi di festa compare subito la schermata a tema; il resto (importazioni pesanti, database,
    # costruzione della finestra) si fa dopo, mentre l'utente la guarda.
    splash = _start_seasonal_splash(db_file)
    if splash is not None:
        # I puntini si animano ora e non a fine avvio: ogni aggiornamento della schermata fa elaborare gli
        # eventi in coda, e a finestra principale già costruita (ma non mostrata) la rimpiccioliscono.
        _animate_splash_dots(splash)
    # Prima di connect(): così la copia del giorno precede anche un'eventuale migrazione
    # dello schema fatta da una versione nuova del programma.
    try:
        daily_backup_if_needed(db_file)
    except OSError:
        pass
    if getattr(sys, "frozen", False):
        # Se questo avvio segue un aggiornamento, l'installazione è riuscita: via le copie vecchie.
        cleanup_leftovers(app_dir())
    conn = connect(db_file)
    set_language(get_setting(conn, "language", DEFAULT_LANGUAGE))

    from gilda_app.ui.main_window import MainWindow

    window = MainWindow(conn, db_file)
    instance.activation_requested.connect(lambda: _bring_to_front(window))
    window.refresh_all()
    if splash is None:
        _animate_splash_dots()
    # Finestra mostrata prima di chiudere lo splash: altrimenti Windows non ha una
    # finestra in primo piano da cui passare il focus e l'app parte in background.
    window.show()
    if splash is not None:
        splash.finish(window)
    _close_splash()
    window.raise_()
    window.activateWindow()
    _maybe_run_initial_import(conn, db_file, window)
    window.refresh_all()
    # Dopo che la finestra è comparsa, senza trattenere l'avvio.
    QTimer.singleShot(500, window.maybe_show_whats_new)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
