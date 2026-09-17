from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QCompleter, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget
from qfluentwidgets import CalendarPicker, CheckBox, EditableComboBox, LineEdit, MessageBoxBase, PlainTextEdit, StrongBodyLabel, SubtitleLabel

from gilda_app.i18n import tr
from gilda_app.models.member import STATUS_ATTIVO, STATUS_EX_MEMBRO, Member, status_label
from gilda_app.utils.countries import canonical_name, country_choices
from gilda_app.utils.flags import display_nation


def _format_history_line(row) -> str:
    date = row["changed_at"][:10]
    if row["previous_status"] is None:
        line = tr("history.joined", date=date, status=status_label(row["new_status"]))
    elif row["previous_status"] == STATUS_EX_MEMBRO and row["new_status"] == STATUS_ATTIVO:
        line = tr("history.rejoined", date=date)
    else:
        line = tr(
            "history.transition",
            date=date,
            prev=status_label(row["previous_status"]),
            new=status_label(row["new_status"]),
        )
    if row["note"]:
        line += tr("history.note_suffix", note=row["note"])
    return line


def _make_nation_combo(parent, placeholder: str) -> EditableComboBox:
    choices = country_choices()
    combo = EditableComboBox(parent)
    combo.setPlaceholderText(placeholder)
    combo.addItems(choices)
    # addItems seleziona automaticamente il primo elemento della lista: lo annulliamo
    # per lasciare il campo vuoto finche' l'utente non sceglie/digita una nazione.
    combo.setCurrentIndex(-1)
    completer = QCompleter(choices, combo)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchContains)
    completer.setCompletionMode(QCompleter.PopupCompletion)
    combo.setCompleter(completer)
    return combo


class MemberDialog(MessageBoxBase):
    """Form di inserimento/modifica membro. Family Name obbligatorio."""

    def __init__(self, parent=None, member: Member | None = None, history: list | None = None):
        super().__init__(parent)
        self.member = member
        is_edit = member is not None

        self.titleLabel = SubtitleLabel(tr("dialog.edit_member.title") if is_edit else tr("dialog.new_member.title"), self)
        self.viewLayout.addWidget(self.titleLabel)

        self.family_edit = LineEdit(self)
        self.family_edit.setPlaceholderText(tr("field.family_name.placeholder"))
        self.main_edit = LineEdit(self)
        self.main_edit.setPlaceholderText(tr("field.main_name.placeholder"))
        self.discord_edit = LineEdit(self)
        self.discord_edit.setPlaceholderText(tr("field.discord_name.placeholder"))
        self.nation1_edit = _make_nation_combo(self, tr("field.nation1.placeholder"))
        self.nation2_edit = _make_nation_combo(self, tr("field.nation2.placeholder"))

        self.date_check = CheckBox(tr("field.date_check"), self)
        self.date_picker = CalendarPicker(self)
        self.date_picker.setDate(QDate.currentDate())
        date_row = QWidget(self)
        date_layout = QHBoxLayout(date_row)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.addWidget(self.date_check)
        date_layout.addWidget(self.date_picker)
        self.date_check.toggled.connect(self.date_picker.setEnabled)

        self.note_edit = PlainTextEdit(self)
        self.note_edit.setPlaceholderText(tr("field.note.placeholder"))
        self.note_edit.setFixedHeight(70)

        self.error_label = QLabel(self)
        self.error_label.setStyleSheet("color: #c42b1c;")
        self.error_label.hide()

        for label_key, widget in [
            ("label.family_name", self.family_edit),
            ("label.main_name", self.main_edit),
            ("label.discord_name", self.discord_edit),
            ("label.nation1", self.nation1_edit),
            ("label.nation2", self.nation2_edit),
        ]:
            self.viewLayout.addWidget(QLabel(tr(label_key), self))
            self.viewLayout.addWidget(widget)

        self.viewLayout.addWidget(date_row)
        self.viewLayout.addWidget(QLabel(tr("label.note"), self))
        self.viewLayout.addWidget(self.note_edit)

        if is_edit:
            self.viewLayout.addWidget(StrongBodyLabel(tr("label.history"), self))
            history_container = QWidget(self)
            history_layout = QVBoxLayout(history_container)
            history_layout.setContentsMargins(0, 0, 0, 0)
            history_layout.setSpacing(2)
            if history:
                for row in history:
                    history_layout.addWidget(QLabel(_format_history_line(row), history_container))
            else:
                history_layout.addWidget(QLabel(tr("history.empty"), history_container))
            history_layout.addStretch(1)

            history_scroll = QScrollArea(self)
            history_scroll.setWidget(history_container)
            history_scroll.setWidgetResizable(True)
            history_scroll.setFixedHeight(140)
            self.viewLayout.addWidget(history_scroll)

        self.viewLayout.addWidget(self.error_label)
        self.widget.setMinimumWidth(380)

        if member is not None:
            self.family_edit.setText(member.family_name)
            self.main_edit.setText(member.main_name)
            self.discord_edit.setText(member.discord_name)
            if len(member.nations) > 0:
                self.nation1_edit.setText(display_nation(member.nations[0]))
            if len(member.nations) > 1:
                self.nation2_edit.setText(display_nation(member.nations[1]))
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

        self.yesButton.setText(tr("button.save"))
        self.cancelButton.setText(tr("button.cancel"))

    def validate(self) -> bool:
        if not self.family_edit.text().strip():
            self.error_label.setText(tr("error.family_name_required"))
            self.error_label.show()
            return False
        return True

    def values(self) -> dict:
        nations = [
            canonical_name(n.strip())
            for n in (self.nation1_edit.text(), self.nation2_edit.text())
            if n.strip()
        ]
        data_inserimento = self.date_picker.getDate().toString("yyyy-MM-dd") if self.date_check.isChecked() else None
        return {
            "family_name": self.family_edit.text().strip(),
            "main_name": self.main_edit.text().strip(),
            "discord_name": self.discord_edit.text().strip(),
            "nations": nations,
            "note": self.note_edit.toPlainText().strip() or None,
            "data_inserimento": data_inserimento,
        }
