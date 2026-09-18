from PySide6.QtWidgets import QLabel
from qfluentwidgets import CheckBox, ComboBox, MessageBoxBase, PlainTextEdit, SubtitleLabel

from gilda_app.i18n import tr
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO, Member, status_label

ALL_STATUSES = [STATUS_ATTIVO, STATUS_EX_MEMBRO, STATUS_BANNATO]


class MoveDialog(MessageBoxBase):
    """Conferma spostamento di un membro verso un'altra lista, con nota opzionale."""

    def __init__(self, parent=None, member: Member = None):
        super().__init__(parent)
        self.member = member

        self.titleLabel = SubtitleLabel(tr("dialog.move.title", name=member.family_name), self)
        self.viewLayout.addWidget(self.titleLabel)

        current_label = QLabel(tr("dialog.move.current_list", status=status_label(member.status)), self)
        self.viewLayout.addWidget(current_label)

        self.viewLayout.addWidget(QLabel(tr("dialog.move.target_label"), self))
        self.target_combo = ComboBox(self)
        for status in ALL_STATUSES:
            if status != member.status:
                self.target_combo.addItem(status_label(status), userData=status)
        self.viewLayout.addWidget(self.target_combo)

        # Ha senso solo spostando verso ex membro: chi lascia la gilda in gioco a volte
        # resta comunque nel canale Discord. Visibile solo quando è quella la scelta nel
        # combo, non per gli altri spostamenti dove la domanda non ha senso.
        self.discord_check = CheckBox(tr("dialog.move.still_on_discord"), self)
        self.viewLayout.addWidget(self.discord_check)
        self.target_combo.currentIndexChanged.connect(self._update_discord_check_visibility)
        self._update_discord_check_visibility()

        self.viewLayout.addWidget(QLabel(tr("dialog.move.note_label"), self))
        self.note_edit = PlainTextEdit(self)
        self.note_edit.setFixedHeight(70)
        self.viewLayout.addWidget(self.note_edit)

        self.widget.setMinimumWidth(360)
        self.yesButton.setText(tr("button.confirm_move"))
        self.cancelButton.setText(tr("button.cancel"))

    def target_status(self) -> str:
        return self.target_combo.currentData()

    def note(self) -> str | None:
        return self.note_edit.toPlainText().strip() or None

    def still_on_discord(self) -> bool | None:
        if self.target_status() != STATUS_EX_MEMBRO:
            return None
        return self.discord_check.isChecked()

    def _update_discord_check_visibility(self) -> None:
        self.discord_check.setVisible(self.target_status() == STATUS_EX_MEMBRO)
