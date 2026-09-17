from PySide6.QtWidgets import QLabel
from qfluentwidgets import LineEdit, MessageBoxBase, SubtitleLabel

CONFIRM_WORD = "AZZERA"


class ResetConfirmDialog(MessageBoxBase):
    """Secondo livello di conferma per l'azzeramento del database: bisogna digitare una parola."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("Conferma azzeramento database", self)
        self.viewLayout.addWidget(self.titleLabel)

        self.viewLayout.addWidget(
            QLabel(
                "Questa azione elimina definitivamente TUTTI i membri e lo storico movimenti.\n"
                f"Verrà comunque creato un backup automatico prima di procedere.\n\n"
                f"Per confermare, digita \"{CONFIRM_WORD}\" qui sotto:",
                self,
            )
        )
        self.confirm_edit = LineEdit(self)
        self.confirm_edit.setPlaceholderText(CONFIRM_WORD)
        self.viewLayout.addWidget(self.confirm_edit)

        self.error_label = QLabel(self)
        self.error_label.setStyleSheet("color: #c42b1c;")
        self.error_label.hide()
        self.viewLayout.addWidget(self.error_label)

        self.widget.setMinimumWidth(360)
        self.yesButton.setText("Azzera definitivamente")
        self.cancelButton.setText("Annulla")

    def validate(self) -> bool:
        if self.confirm_edit.text().strip() != CONFIRM_WORD:
            self.error_label.setText(f'Devi digitare esattamente "{CONFIRM_WORD}" per confermare.')
            self.error_label.show()
            return False
        return True
