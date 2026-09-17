from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCompleter,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)
from qfluentwidgets import CalendarPicker, CheckBox, EditableComboBox, LineEdit, MessageBoxBase, PlainTextEdit, StrongBodyLabel, SubtitleLabel

from gilda_app.db.database import get_status_history, update_status_history_entry
from gilda_app.i18n import tr
from gilda_app.models.member import Member
from gilda_app.ui.history_entry_dialog import HistoryEntryDialog
from gilda_app.utils.countries import canonical_name, country_choices
from gilda_app.utils.flags import display_nation
from gilda_app.utils.history_format import format_history_line


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
    """Form di inserimento/modifica membro. Family Name obbligatorio.

    In modifica mostra anche lo storico movimenti, corregibile sul posto (doppio
    click su una voce): questa parte scrive direttamente sul database invece di
    passare da values(), perché deve riflettersi subito mentre il dialog resta aperto.
    """

    def __init__(self, parent=None, member: Member | None = None, conn=None):
        super().__init__(parent)
        self.member = member
        self.conn = conn
        self._history_rows: list = []
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

        if is_edit and conn is not None:
            self.viewLayout.addWidget(StrongBodyLabel(tr("label.history"), self))
            self.history_table = QTableWidget(self)
            self.history_table.setColumnCount(1)
            self.history_table.horizontalHeader().hide()
            self.history_table.verticalHeader().hide()
            self.history_table.horizontalHeader().setStretchLastSection(True)
            self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.history_table.setSelectionMode(QAbstractItemView.SingleSelection)
            self.history_table.setFixedHeight(140)
            self.history_table.doubleClicked.connect(self._on_history_double_click)
            self.viewLayout.addWidget(self.history_table)
            self.viewLayout.addWidget(QLabel(tr("history.hint"), self))
            self._refresh_history()

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

    def _refresh_history(self) -> None:
        self._history_rows = get_status_history(self.conn, self.member.id)
        if not self._history_rows:
            self.history_table.setRowCount(1)
            item = QTableWidgetItem(tr("history.empty"))
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
            self.history_table.setItem(0, 0, item)
            return

        self.history_table.setRowCount(len(self._history_rows))
        for row_idx, row in enumerate(self._history_rows):
            item = QTableWidgetItem(format_history_line(row))
            self.history_table.setItem(row_idx, 0, item)

    def _on_history_double_click(self, index) -> None:
        row = index.row()
        if row >= len(self._history_rows):
            return
        history_row = self._history_rows[row]
        dialog = HistoryEntryDialog(self, history_row)
        if dialog.exec():
            values = dialog.values()
            update_status_history_entry(self.conn, history_row["id"], values["date"], values["note"])
            self._refresh_history()
            if history_row["previous_status"] is None:
                # la correzione ha aggiornato anche members.data_inserimento: riflettila nel form
                self.date_check.setChecked(True)
                self.date_picker.setDate(QDate.fromString(values["date"], "yyyy-MM-dd"))

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
