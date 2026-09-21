from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCompleter,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)
from qfluentwidgets import (
    CheckBox,
    EditableComboBox,
    LineEdit,
    MessageBoxBase,
    PlainTextEdit,
    RadioButton,
    StrongBodyLabel,
    SubtitleLabel,
)

from gilda_app.db.database import get_status_history, update_status_history_entry
from gilda_app.i18n import tr
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO, Member, status_label
from gilda_app.ui.fast_calendar_picker import FastCalendarPicker
from gilda_app.ui.history_entry_dialog import HistoryEntryDialog
from gilda_app.utils.countries import canonical_name, country_choices
from gilda_app.utils.flags import display_nation
from gilda_app.utils.history_format import format_history_line

NEW_MEMBER_STATUSES = [STATUS_ATTIVO, STATUS_EX_MEMBRO, STATUS_BANNATO]

# Tetto all'altezza di una riga di storico con nota lunga: circa 3 righe di testo.
MAX_HISTORY_ROW_HEIGHT = 78


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

    def __init__(self, parent=None, member: Member | None = None, conn=None, status: str | None = None):
        super().__init__(parent)
        self.member = member
        self.conn = conn
        self._history_rows: list = []
        is_edit = member is not None
        target_status = member.status if is_edit else status

        self.titleLabel = SubtitleLabel(tr("dialog.edit_member.title") if is_edit else tr("dialog.new_member.title"), self)
        self.viewLayout.addWidget(self.titleLabel)

        # Solo per un nuovo membro: scelta della lista in cui inserirlo, con preselezionata
        # quella della scheda da cui si è premuto "Aggiungi". In modifica non c'è: per
        # cambiare lista si usa lo spostamento, che registra storico e backup.
        self._status_buttons: dict[str, RadioButton] = {}
        if not is_edit:
            self.viewLayout.addWidget(QLabel(tr("label.list"), self))
            status_row = QWidget(self)
            status_layout = QHBoxLayout(status_row)
            status_layout.setContentsMargins(0, 0, 0, 0)
            status_group = QButtonGroup(self)
            for st in NEW_MEMBER_STATUSES:
                button = RadioButton(status_label(st), status_row)
                status_group.addButton(button)
                status_layout.addWidget(button)
                self._status_buttons[st] = button
            status_layout.addStretch(1)
            self._status_buttons[status if status in self._status_buttons else STATUS_ATTIVO].setChecked(True)
            self.viewLayout.addWidget(status_row)

        self.family_edit = LineEdit(self)
        self.family_edit.setPlaceholderText(tr("field.family_name.placeholder"))
        self.main_edit = LineEdit(self)
        self.main_edit.setPlaceholderText(tr("field.main_name.placeholder"))
        self.discord_edit = LineEdit(self)
        self.discord_edit.setPlaceholderText(tr("field.discord_name.placeholder"))
        self.nation1_edit = _make_nation_combo(self, tr("field.nation1.placeholder"))
        self.nation2_edit = _make_nation_combo(self, tr("field.nation2.placeholder"))

        self.date_check = CheckBox(tr("field.date_check"), self)
        self.date_picker = FastCalendarPicker(self)
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

        # Ha senso solo per un ex membro: è ancora presente nel canale Discord della
        # gilda pur non essendo più tra i membri attivi in gioco. Per gli altri stati
        # non si mostra proprio, invece di lasciarla sempre visibile ma inutile.
        # Per un nuovo membro la lista si sceglie nel form, quindi la spunta esiste sempre
        # e si mostra solo quando la lista scelta è Ex membri.
        needs_discord_check = target_status == STATUS_EX_MEMBRO or not is_edit
        self.discord_check = CheckBox(tr("field.still_on_discord"), self) if needs_discord_check else None

        for label_key, widget in [
            ("label.family_name", self.family_edit),
            ("label.main_name", self.main_edit),
            ("label.discord_name", self.discord_edit),
            ("label.nation1", self.nation1_edit),
            ("label.nation2", self.nation2_edit),
        ]:
            self.viewLayout.addWidget(QLabel(tr(label_key), self))
            self.viewLayout.addWidget(widget)
            if widget is self.discord_edit and self.discord_check is not None:
                self.viewLayout.addWidget(self.discord_check)

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
            # Le voci con nota lunga (es. motivo di uno spostamento) andavano tagliate:
            # word wrap + altezza riga adattata le mandano a capo invece di troncarle.
            self.history_table.setWordWrap(True)
            self.history_table.setTextElideMode(Qt.ElideNone)
            self.history_table.setFixedHeight(160)
            self.history_table.doubleClicked.connect(self._on_history_double_click)
            self.viewLayout.addWidget(self.history_table)
            self.viewLayout.addWidget(QLabel(tr("history.hint"), self))
            self._refresh_history()

        self.viewLayout.addWidget(self.error_label)
        # Form più largo: 380px era stretto e tagliava le voci di storico più lunghe.
        self.widget.setMinimumWidth(520)

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
            if self.discord_check is not None:
                self.discord_check.setChecked(member.still_on_discord)

            if member.data_inserimento:
                self.date_check.setChecked(True)
                self.date_picker.setDate(QDate.fromString(member.data_inserimento[:10], "yyyy-MM-dd"))
            else:
                self.date_check.setChecked(False)
                self.date_picker.setEnabled(False)
        else:
            self.date_check.setChecked(True)

        for button in self._status_buttons.values():
            button.toggled.connect(self._update_discord_check_visibility)
        self._update_discord_check_visibility()

        self.yesButton.setText(tr("button.save"))
        self.cancelButton.setText(tr("button.cancel"))

    def selected_status(self) -> str | None:
        """Lista scelta per un nuovo membro; per un membro esistente la sua lista attuale."""
        if self.member is not None:
            return self.member.status
        for st, button in self._status_buttons.items():
            if button.isChecked():
                return st
        return None

    def _update_discord_check_visibility(self, *_args) -> None:
        if self.discord_check is not None and not self.member:
            self.discord_check.setVisible(self.selected_status() == STATUS_EX_MEMBRO)

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
            line = format_history_line(row)
            item = QTableWidgetItem(line)
            item.setToolTip(line)  # testo completo al passaggio del mouse
            self.history_table.setItem(row_idx, 0, item)
        # Adatta l'altezza di ogni riga al testo mandato a capo, ma con un tetto: una
        # nota molto lunga faceva diventare la riga altissima. Oltre il tetto la riga
        # resta compatta (2-3 righe) e il testo intero è comunque nel tooltip.
        self.history_table.resizeRowsToContents()
        for row_idx in range(self.history_table.rowCount()):
            if self.history_table.rowHeight(row_idx) > MAX_HISTORY_ROW_HEIGHT:
                self.history_table.setRowHeight(row_idx, MAX_HISTORY_ROW_HEIGHT)

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
            "status": self.selected_status(),
            "still_on_discord": (
                self.discord_check.isChecked()
                if self.discord_check is not None and self.selected_status() == STATUS_EX_MEMBRO
                else None
            ),
        }
