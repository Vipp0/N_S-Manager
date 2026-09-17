from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QCompleter, QHBoxLayout, QLabel, QWidget
from qfluentwidgets import CalendarPicker, CheckBox, EditableComboBox, LineEdit, MessageBoxBase, PlainTextEdit, SubtitleLabel

from gilda_app.models.member import Member
from gilda_app.utils.countries import ALL_COUNTRIES


def _make_nation_combo(parent, placeholder: str) -> EditableComboBox:
    combo = EditableComboBox(parent)
    combo.setPlaceholderText(placeholder)
    combo.addItems(ALL_COUNTRIES)
    # addItems seleziona automaticamente il primo elemento della lista: lo annulliamo
    # per lasciare il campo vuoto finche' l'utente non sceglie/digita una nazione.
    combo.setCurrentIndex(-1)
    completer = QCompleter(ALL_COUNTRIES, combo)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchContains)
    completer.setCompletionMode(QCompleter.PopupCompletion)
    combo.setCompleter(completer)
    return combo


class MemberDialog(MessageBoxBase):
    """Form di inserimento/modifica membro. Family Name obbligatorio."""

    def __init__(self, parent=None, member: Member | None = None):
        super().__init__(parent)
        self.member = member
        is_edit = member is not None

        self.titleLabel = SubtitleLabel("Modifica membro" if is_edit else "Nuovo membro", self)
        self.viewLayout.addWidget(self.titleLabel)

        self.family_edit = LineEdit(self)
        self.family_edit.setPlaceholderText("Family Name (obbligatorio)")
        self.main_edit = LineEdit(self)
        self.main_edit.setPlaceholderText("Main Name")
        self.discord_edit = LineEdit(self)
        self.discord_edit.setPlaceholderText("Discord Name")
        self.nation1_edit = _make_nation_combo(self, "Nazione")
        self.nation2_edit = _make_nation_combo(self, "Seconda nazione (opzionale)")

        self.date_check = CheckBox("Registra la data di ingresso in gilda", self)
        self.date_picker = CalendarPicker(self)
        self.date_picker.setDate(QDate.currentDate())
        date_row = QWidget(self)
        date_layout = QHBoxLayout(date_row)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.addWidget(self.date_check)
        date_layout.addWidget(self.date_picker)
        self.date_check.toggled.connect(self.date_picker.setEnabled)

        self.note_edit = PlainTextEdit(self)
        self.note_edit.setPlaceholderText("Note")
        self.note_edit.setFixedHeight(70)

        self.error_label = QLabel(self)
        self.error_label.setStyleSheet("color: #c42b1c;")
        self.error_label.hide()

        for label_text, widget in [
            ("Family Name", self.family_edit),
            ("Main Name", self.main_edit),
            ("Discord Name", self.discord_edit),
            ("Nazione 1", self.nation1_edit),
            ("Nazione 2", self.nation2_edit),
        ]:
            self.viewLayout.addWidget(QLabel(label_text, self))
            self.viewLayout.addWidget(widget)

        self.viewLayout.addWidget(date_row)
        self.viewLayout.addWidget(QLabel("Note", self))
        self.viewLayout.addWidget(self.note_edit)
        self.viewLayout.addWidget(self.error_label)
        self.widget.setMinimumWidth(360)

        if member is not None:
            self.family_edit.setText(member.family_name)
            self.main_edit.setText(member.main_name)
            self.discord_edit.setText(member.discord_name)
            if len(member.nations) > 0:
                self.nation1_edit.setText(member.nations[0])
            if len(member.nations) > 1:
                self.nation2_edit.setText(member.nations[1])
            if member.note:
                self.note_edit.setPlainText(member.note)

            if member.data_inserimento:
                self.date_check.setChecked(True)
                self.date_picker.setDate(QDate.fromString(member.data_inserimento[:10], "yyyy-MM-dd"))
            else:
                self.date_check.setChecked(False)
                self.date_picker.setEnabled(False)
        else:
            self.date_check.setChecked(True)

        self.yesButton.setText("Salva")
        self.cancelButton.setText("Annulla")

    def validate(self) -> bool:
        if not self.family_edit.text().strip():
            self.error_label.setText("Family Name è obbligatorio.")
            self.error_label.show()
            return False
        return True

    def values(self) -> dict:
        nations = [n.strip() for n in (self.nation1_edit.text(), self.nation2_edit.text()) if n.strip()]
        data_inserimento = self.date_picker.getDate().toString("yyyy-MM-dd") if self.date_check.isChecked() else None
        return {
            "family_name": self.family_edit.text().strip(),
            "main_name": self.main_edit.text().strip(),
            "discord_name": self.discord_edit.text().strip(),
            "nations": nations,
            "note": self.note_edit.toPlainText().strip() or None,
            "data_inserimento": data_inserimento,
        }
