from PySide6.QtWidgets import QLabel
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import MessageBoxBase, PushButton, SubtitleLabel

from gilda_app.i18n import tr
from gilda_app.models.member import status_label


class DuplicateMemberDialog(MessageBoxBase):
    """Avviso "questo Family Name esiste già", con le persone trovate (in qualunque lista) e,
    per ognuna, il pulsante per aprirne la scheda invece di crearne un doppione. Si può
    anche andare avanti comunque (es. due giocatori diversi con lo stesso nome in regioni
    diverse) o tornare al modulo. Chi lo apre legge open_member_id: se non è None, è stata
    scelta la scheda di quel membro."""

    def __init__(self, parent, name: str, matches, is_edit: bool):
        super().__init__(parent)
        self.open_member_id: int | None = None

        self.titleLabel = SubtitleLabel(tr("duplicate.title"), self)
        self.viewLayout.addWidget(self.titleLabel)
        intro = QLabel(tr("duplicate.body_edit" if is_edit else "duplicate.body_new", name=name), self)
        intro.setWordWrap(True)
        self.viewLayout.addWidget(intro)

        for row in matches:
            main = f" ({row['main_name']})" if row["main_name"] else ""
            label = f"{row['family_name']}{main} — {status_label(row['status'])}"
            self.viewLayout.addWidget(QLabel(label, self))
        hint = QLabel(tr("duplicate.hint"), self)
        hint.setWordWrap(True)
        self.viewLayout.addWidget(hint)

        for row in matches:
            button = PushButton(FIF.PEOPLE, tr("duplicate.open", name=row["family_name"], status=status_label(row["status"])), self)
            button.clicked.connect(lambda _=False, member_id=row["id"]: self._open(member_id))
            self.viewLayout.addWidget(button)

        self.widget.setMinimumWidth(480)
        self.yesButton.setText(tr("duplicate.save_anyway" if is_edit else "duplicate.add_anyway"))
        self.cancelButton.setText(tr("duplicate.back"))

    def _open(self, member_id: int) -> None:
        self.open_member_id = member_id
        self.reject()
