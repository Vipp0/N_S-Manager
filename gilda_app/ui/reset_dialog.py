from PySide6.QtWidgets import QLabel
from qfluentwidgets import LineEdit, MessageBoxBase, SubtitleLabel

from gilda_app.i18n import get_language, tr

_CONFIRM_WORDS = {"it": "AZZERA", "en": "RESET"}


def _confirm_word() -> str:
    return _CONFIRM_WORDS.get(get_language(), "RESET")


class ResetConfirmDialog(MessageBoxBase):
    """Secondo livello di conferma per l'azzeramento del database: bisogna digitare una parola."""

    def __init__(self, parent=None):
        super().__init__(parent)
        word = _confirm_word()

        self.titleLabel = SubtitleLabel(tr("dialog.reset_confirm.title"), self)
        self.viewLayout.addWidget(self.titleLabel)

        self.viewLayout.addWidget(QLabel(tr("dialog.reset_confirm.body", word=word), self))
        self.confirm_edit = LineEdit(self)
        self.confirm_edit.setPlaceholderText(word)
        self.viewLayout.addWidget(self.confirm_edit)

        self.error_label = QLabel(self)
        self.error_label.setStyleSheet("color: #c42b1c;")
        self.error_label.hide()
        self.viewLayout.addWidget(self.error_label)

        self.widget.setMinimumWidth(360)
        self.yesButton.setText(tr("button.confirm_reset"))
        self.cancelButton.setText(tr("button.cancel"))

    def validate(self) -> bool:
        if self.confirm_edit.text().strip() != _confirm_word():
            self.error_label.setText(tr("dialog.reset_confirm.error", word=_confirm_word()))
            self.error_label.show()
            return False
        return True
