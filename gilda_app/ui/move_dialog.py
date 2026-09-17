from PySide6.QtWidgets import QLabel
from qfluentwidgets import ComboBox, MessageBoxBase, PlainTextEdit, SubtitleLabel

from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO, STATUS_LABELS, Member

ALL_STATUSES = [STATUS_ATTIVO, STATUS_EX_MEMBRO, STATUS_BANNATO]


class MoveDialog(MessageBoxBase):
    """Conferma spostamento di un membro verso un'altra lista, con nota opzionale."""

    def __init__(self, parent=None, member: Member = None):
        super().__init__(parent)
        self.member = member

        self.titleLabel = SubtitleLabel(f"Sposta {member.family_name}", self)
        self.viewLayout.addWidget(self.titleLabel)

        current_label = QLabel(f"Lista attuale: {STATUS_LABELS[member.status]}", self)
        self.viewLayout.addWidget(current_label)

        self.viewLayout.addWidget(QLabel("Sposta in:", self))
        self.target_combo = ComboBox(self)
        for status in ALL_STATUSES:
            if status != member.status:
                self.target_combo.addItem(STATUS_LABELS[status], userData=status)
        self.viewLayout.addWidget(self.target_combo)

        self.viewLayout.addWidget(QLabel("Nota (opzionale, es. motivo del ban):", self))
        self.note_edit = PlainTextEdit(self)
        self.note_edit.setFixedHeight(70)
        self.viewLayout.addWidget(self.note_edit)

        self.widget.setMinimumWidth(360)
        self.yesButton.setText("Conferma spostamento")
        self.cancelButton.setText("Annulla")

    def target_status(self) -> str:
        return self.target_combo.currentData()

    def note(self) -> str | None:
        return self.note_edit.toPlainText().strip() or None
