"""Schermata "aggiornamento in corso": il logo di caricamento con una barra di avanzamento.

La usano entrambi i processi dell'aggiornamento (vedi utils/updater.py), così per chi guarda
è un'unica schermata: l'app in uso porta la barra da 0 a 70% (scaricamento e preparazione dei
file), la nuova versione da 70 a 100% (sostituzione e riavvio)."""
import shutil
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QFont, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QProgressBar, QWidget

from gilda_app.i18n import set_language, tr
from gilda_app.utils import updater
from gilda_app.utils.update_check import ReleaseInfo

RESOURCES = Path(__file__).resolve().parent.parent / "resources"
SPLASH_PATH = RESOURCES / "splash.png"
APP_ICON_PATH = RESOURCES / "app_icon.png"

DOWNLOAD_END = 55  # % della barra alla fine dello scaricamento
PREPARE_END = 70  # % alla fine della preparazione dei file (fine della fase 1)
INSTALL_END = 98  # % alla fine della copia dei file nuovi (fine della fase 2, poi riavvio)


class UpdateProgressWindow(QWidget):
    def __init__(self):
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint)
        self._background = QPixmap(str(SPLASH_PATH))
        self.setFixedSize(self._background.size())
        self.setWindowTitle("Night_Shade Manager")
        self.setWindowIcon(QIcon(str(APP_ICON_PATH)))

        width, height = self.width(), self.height()
        self._title = QLabel(tr("update.window.title"), self)
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setGeometry(0, height - 92, width, 28)
        title_font = QFont("Segoe UI", 14)
        title_font.setBold(True)
        self._title.setFont(title_font)
        self._title.setStyleSheet("color: #e6d9ff; background: transparent;")

        bar_width = 420
        self._bar = QProgressBar(self)
        self._bar.setRange(0, 100)
        self._bar.setTextVisible(False)
        self._bar.setGeometry((width - bar_width) // 2, height - 56, bar_width, 8)
        self._bar.setStyleSheet(
            "QProgressBar { background: #1c1430; border: none; border-radius: 4px; }"
            "QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            " stop:0 #6d3fd1, stop:1 #b58cff); border-radius: 4px; }"
        )

        self._step = QLabel("", self)
        self._step.setAlignment(Qt.AlignCenter)
        self._step.setGeometry(0, height - 42, width, 24)
        self._step.setFont(QFont("Segoe UI", 10))
        self._step.setStyleSheet("color: #a897d6; background: transparent;")

        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            self.move(screen.availableGeometry().center() - self.rect().center())

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._background)

    def set_progress(self, percent: int, step_text: str | None = None) -> None:
        self._bar.setValue(max(0, min(100, percent)))
        if step_text is not None:
            self._step.setText(step_text)


# -- fase 1, nell'app in uso ---------------------------------------------------
class UpdateDownloadWorker(QObject):
    """Scarica e prepara l'aggiornamento in un thread, aggiornando la barra dal thread Qt."""

    progress = Signal(int, str)
    finished = Signal(str)  # messaggio d'errore, vuoto se è andato tutto bene

    def __init__(self, info: ReleaseInfo, app_dir: Path):
        super().__init__()
        self._info = info
        self._app_dir = app_dir

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        version = self._info.tag.lstrip("vV")
        try:
            work = updater.update_dir(self._app_dir)
            shutil.rmtree(work, ignore_errors=True)
            work.mkdir(parents=True, exist_ok=True)
            zip_path = work / "download.zip"
            self.progress.emit(0, tr("update.step.download", version=version))
            updater.download_release(
                self._info, zip_path, lambda f, _key: self.progress.emit(int(f * DOWNLOAD_END), "")
            )
            self.progress.emit(DOWNLOAD_END, tr("update.step.extract"))
            updater.extract_release(
                zip_path,
                updater.stage_dir(self._app_dir),
                lambda f, _key: self.progress.emit(int(DOWNLOAD_END + f * (PREPARE_END - DOWNLOAD_END)), ""),
            )
            zip_path.unlink(missing_ok=True)
            self.progress.emit(PREPARE_END, tr("update.step.wait"))
        except updater.UpdateError as exc:
            self.finished.emit(str(exc) or "error")
        except Exception as exc:  # qualunque imprevisto: l'app in uso resta com'è
            self.finished.emit(str(exc) or "error")
        else:
            self.finished.emit("")


# -- fase 2, nella nuova versione ----------------------------------------------
def run_apply_mode(args: list[str], close_splash=lambda: None) -> int:
    """Eseguita dalla NUOVA versione lanciata con --apply-update <cartella> <pid> <lingua>."""
    target = Path(args[0])
    pid = int(args[1])
    set_language(args[2] if len(args) > 2 else "it")

    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 11))
    window = UpdateProgressWindow()
    window.set_progress(PREPARE_END, tr("update.step.wait"))
    window.show()
    close_splash()
    app.processEvents()

    # Attende la chiusura dell'app in uso, tenendo viva la finestra.
    deadline = time.time() + 60
    while not updater.wait_for_exit(pid, timeout=0.1) and time.time() < deadline:
        app.processEvents()

    span = INSTALL_END - PREPARE_END

    def on_progress(fraction: float, key: str | None) -> None:
        window.set_progress(int(PREPARE_END + fraction * span), tr(key) if key else None)
        app.processEvents()

    try:
        updater.apply_staged_update(updater.stage_dir(target), target, on_progress)
    except updater.UpdateError as exc:
        window.hide()
        QMessageBox.critical(None, tr("update.failed.title"), tr("update.apply_failed.body", error=str(exc)))
        updater.relaunch(target)
        return 1
    window.set_progress(100, tr("update.step.restart"))
    app.processEvents()
    time.sleep(0.6)
    updater.relaunch(target)
    return 0
