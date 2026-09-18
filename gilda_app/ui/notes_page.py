from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import PlainTextEdit, SubtitleLabel

from gilda_app.db.database import get_setting, set_setting
from gilda_app.i18n import tr

NOTES_SETTING_KEY = "notes_content"
# Ritardo dopo l'ultima battitura prima di salvare: evita una scrittura sul DB a ogni
# singolo carattere digitato, che con un blocco note pensato per essere usato a lungo
# diventerebbe comunque una scrittura molto frequente e inutile.
AUTOSAVE_DELAY_MS = 800


class NotesPage(QWidget):
    """Blocco note libero della gilda: un'unica nota testuale condivisa, salvata in
    app_settings (stessa tabella già usata per la lingua), senza bisogno di una nuova
    tabella dedicata."""

    def __init__(self, get_conn, parent=None):
        super().__init__(parent)
        self.get_conn = get_conn

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(SubtitleLabel(tr("nav.notes"), self))

        self.editor = PlainTextEdit(self)
        self.editor.setPlaceholderText(tr("notes.placeholder"))
        self.editor.setFont(QFont("Segoe UI", 13))
        layout.addWidget(self.editor, 1)

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(AUTOSAVE_DELAY_MS)
        self._save_timer.timeout.connect(self.save)
        self.editor.textChanged.connect(self._save_timer.start)

        self.editor.setPlainText(get_setting(self.get_conn(), NOTES_SETTING_KEY, "") or "")

    def save(self) -> None:
        self._save_timer.stop()
        set_setting(self.get_conn(), NOTES_SETTING_KEY, self.editor.toPlainText())
