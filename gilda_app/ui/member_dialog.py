from PySide6.QtCore import QDate, QEvent, Qt, QTimer
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCompleter,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CheckBox,
    EditableComboBox,
    FluentIcon as FIF,
    LineEdit,
    MessageBoxBase,
    PlainTextEdit,
    PushButton,
    RadioButton,
    ScrollArea,
    StrongBodyLabel,
    SubtitleLabel,
)

from gilda_app.db.database import (
    TRACKED_NAME_FIELDS,
    add_name_change,
    delete_name_change,
    get_name_history,
    get_status_history,
    rebuild_status_history,
    update_name_change,
    update_status_history_entry,
)
from gilda_app.i18n import tr
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO, Member, status_label
from gilda_app.ui.fast_calendar_picker import DateEdit
from gilda_app.ui.history_entry_dialog import HistoryEntryDialog
from gilda_app.ui.name_change_dialog import NameChangeDialog
from gilda_app.ui.rebuild_history_dialog import RebuildHistoryDialog
from gilda_app.utils.countries import canonical_name, country_choices
from gilda_app.utils.flags import display_nation
from gilda_app.utils.date_format import iso_to_display
from gilda_app.utils.history_format import format_history_line

NEW_MEMBER_STATUSES = [STATUS_ATTIVO, STATUS_EX_MEMBRO, STATUS_BANNATO]

# Sfondi pastello delle righe dello storico, per capire a colpo d'occhio di che passaggio si
# tratta: primo ingresso, uscita (ex membro), ban, rientro.
HISTORY_COLOR_JOIN = QColor("#d7f0dc")
HISTORY_COLOR_EX = QColor("#fff2c2")
HISTORY_COLOR_BAN = QColor("#f8d4d4")
HISTORY_COLOR_REJOIN = QColor("#d3e8fa")
NAME_CHANGE_COLOR = QColor("#e6e0f5")


def history_row_color(row) -> QColor:
    if row["new_status"] == STATUS_EX_MEMBRO:
        return HISTORY_COLOR_EX
    if row["new_status"] == STATUS_BANNATO:
        return HISTORY_COLOR_BAN
    return HISTORY_COLOR_JOIN if row["previous_status"] is None else HISTORY_COLOR_REJOIN


# In modifica, se la finestra dell'app è abbastanza larga, dati e storico stanno affiancati
# in due colonne invece di una colonna lunga da scorrere; sotto questa larghezza si torna
# alla colonna singola.
TWO_COLUMN_MIN_PARENT_WIDTH = 1100
TWO_COLUMN_DIALOG_WIDTH = 980

# Tetto all'altezza di una riga di storico con nota lunga: circa 3 righe di testo.
MAX_HISTORY_ROW_HEIGHT = 78


def _section_card(parent, title: str):
    """Riquadro con bordo sottile e titolo, per separare a colpo d'occhio le sezioni
    (storico movimenti, storico nomi) nella colonna di destra."""
    frame = QFrame(parent)
    frame.setObjectName("sectionCard")
    frame.setStyleSheet("#sectionCard { border: 1px solid rgba(0, 0, 0, 45); border-radius: 8px; }")
    box = QVBoxLayout(frame)
    box.setContentsMargins(12, 10, 12, 12)
    box.setSpacing(8)
    box.addWidget(StrongBodyLabel(title, frame))
    return frame, box


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
    click su una voce) o ricostruibile da zero (pulsante dedicato, per inserire a
    posteriori entrate/uscite/rientri già avvenuti): questa parte scrive direttamente
    sul database invece di passare da values(), perché deve riflettersi subito mentre
    il dialog resta aperto.
    """

    def __init__(self, parent=None, member: Member | None = None, conn=None, status: str | None = None):
        super().__init__(parent)
        self.member = member
        self.conn = conn
        self._history_rows: list = []
        # Ricostruire lo storico scrive subito sul database (come la correzione di una
        # singola voce): se poi questo dialog viene chiuso con Annulla, chi lo apre deve
        # comunque aggiornare le liste, perché lo stato del membro può essere cambiato.
        self.history_changed = False
        is_edit = member is not None
        target_status = member.status if is_edit else status

        self.titleLabel = SubtitleLabel(tr("dialog.edit_member.title") if is_edit else tr("dialog.new_member.title"), self)
        self.viewLayout.addWidget(self.titleLabel)

        # Tutti i campi stanno in un'area scorrevole: in una finestra piccola il form
        # (soprattutto in modifica, con lo storico) è più alto della finestra e le parti
        # in alto e in basso si sovrapponevano ai bottoni.
        self._form_widget = QWidget(self)
        self._form_widget.setObjectName("memberFormContent")
        self._form_widget.setStyleSheet("#memberFormContent { background: transparent; }")
        two_column = bool(
            is_edit and conn is not None and parent is not None and parent.width() >= TWO_COLUMN_MIN_PARENT_WIDTH
        )
        root = QHBoxLayout(self._form_widget)
        root.setContentsMargins(0, 0, 12, 0)
        root.setSpacing(28)
        form = QVBoxLayout()
        form.setSpacing(self.viewLayout.spacing())
        root.addLayout(form, 1)
        history_col = form
        if two_column:
            history_col = QVBoxLayout()
            history_col.setSpacing(self.viewLayout.spacing())
            root.addLayout(history_col, 1)
        self._scroll = ScrollArea(self)
        self._scroll.setWidget(self._form_widget)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.enableTransparentBackground()
        self._scroll.setFrameShape(QFrame.NoFrame)
        self.viewLayout.addWidget(self._scroll)

        # Solo per un nuovo membro: scelta della lista in cui inserirlo, con preselezionata
        # quella della scheda da cui si è premuto "Aggiungi". In modifica non c'è: per
        # cambiare lista si usa lo spostamento, che registra storico e backup.
        self._status_buttons: dict[str, RadioButton] = {}
        if not is_edit:
            form.addWidget(QLabel(tr("label.list"), self))
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
            form.addWidget(status_row)

        self.family_edit = LineEdit(self)
        self.family_edit.setPlaceholderText(tr("field.family_name.placeholder"))
        self.main_edit = LineEdit(self)
        self.main_edit.setPlaceholderText(tr("field.main_name.placeholder"))
        self.discord_edit = LineEdit(self)
        self.discord_edit.setPlaceholderText(tr("field.discord_name.placeholder"))
        self.nation1_edit = _make_nation_combo(self, tr("field.nation1.placeholder"))
        self.nation2_edit = _make_nation_combo(self, tr("field.nation2.placeholder"))

        self.date_check = CheckBox(tr("field.date_check"), self)
        self.date_picker = DateEdit(self)
        self.date_picker.setDate(QDate.currentDate())
        self.date_picker.setMinimumWidth(170)
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
            form.addWidget(QLabel(tr(label_key), self))
            form.addWidget(widget)
            if widget is self.discord_edit and self.discord_check is not None:
                form.addWidget(self.discord_check)

        form.addWidget(date_row)
        form.addWidget(QLabel(tr("label.note"), self))
        form.addWidget(self.note_edit)

        if is_edit and conn is not None:
            history_card, history_box = _section_card(self, tr("label.history"))
            history_col.addWidget(history_card)
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
            self.history_table.doubleClicked.connect(self._on_history_double_click)
            self.history_table.viewport().installEventFilter(self)
            if two_column:
                self.history_table.setFixedHeight(140)
                # Larghezza decisa dal layout, non dal testo più lungo: le righe vanno a capo.
                self.history_table.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
                history_box.addWidget(self.history_table)
            else:
                self.history_table.setFixedHeight(140)
                history_box.addWidget(self.history_table)
            history_hint = QLabel(tr("history.hint"), self)
            history_hint.setWordWrap(True)
            history_box.addWidget(history_hint)

            self.rebuild_history_btn = PushButton(FIF.HISTORY, tr("button.rebuild_history"), self)
            self.rebuild_history_btn.clicked.connect(self._on_rebuild_history)
            history_box.addWidget(self.rebuild_history_btn)

            name_card, name_box = _section_card(self, tr("label.name_history"))
            history_col.addWidget(name_card)
            self.name_table = QTableWidget(self)
            self.name_table.setColumnCount(1)
            self.name_table.horizontalHeader().hide()
            self.name_table.verticalHeader().hide()
            self.name_table.horizontalHeader().setStretchLastSection(True)
            self.name_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.name_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.name_table.setSelectionMode(QAbstractItemView.SingleSelection)
            self.name_table.setFixedHeight(76)
            self.name_table.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            self.name_table.doubleClicked.connect(self._on_name_double_click)
            name_box.addWidget(self.name_table)
            name_hint = QLabel(tr("name_history.hint"), self)
            name_hint.setWordWrap(True)
            name_box.addWidget(name_hint)
            name_buttons = QHBoxLayout()
            add_name_btn = PushButton(FIF.ADD, tr("name_history.add"), self)
            add_name_btn.clicked.connect(self._on_add_name_change)
            delete_name_btn = PushButton(FIF.DELETE, tr("name_history.delete"), self)
            delete_name_btn.clicked.connect(self._on_delete_name_change)
            name_buttons.addWidget(add_name_btn)
            name_buttons.addWidget(delete_name_btn)
            name_buttons.addStretch(1)
            name_box.addLayout(name_buttons)

            self._refresh_history()
            self._refresh_name_history()

        form.addWidget(self.error_label)
        if two_column:
            form.addStretch(1)
        # Form più largo: 380px era stretto e tagliava le voci di storico più lunghe.
        self.widget.setMinimumWidth(TWO_COLUMN_DIALOG_WIDTH if two_column else 520)

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

    # Spazio della finestra non occupato dal form: titolo, bottoni, margini del riquadro.
    _NON_SCROLL_RESERVE = 205

    def _fit_scroll_height(self) -> None:
        needed = self._form_widget.sizeHint().height() + 2
        available = max(160, self.height() - self._NON_SCROLL_RESERVE)
        self._scroll.setFixedHeight(min(needed, available))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._fit_scroll_height()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit_scroll_height()

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
            self._fit_scroll_height()

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
            item.setBackground(QBrush(history_row_color(row)))
            item.setForeground(QBrush(QColor("#202020")))
            self.history_table.setItem(row_idx, 0, item)
        self._fit_history_rows()

    def _refresh_name_history(self) -> None:
        self._name_rows = get_name_history(self.conn, self.member.id)
        if not self._name_rows:
            self.name_table.setRowCount(1)
            item = QTableWidgetItem(tr("name_history.empty"))
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
            self.name_table.setItem(0, 0, item)
            return
        self.name_table.setRowCount(len(self._name_rows))
        for row_idx, row in enumerate(self._name_rows):
            field_label = tr(f"label.{row['field']}_field")
            date = iso_to_display(row["changed_at"])
            if row["old_value"]:
                line = tr("name_history.line", date=date, field=field_label, old=row["old_value"], new=row["new_value"])
            else:
                line = tr("name_history.line_first", date=date, field=field_label, new=row["new_value"])
            item = QTableWidgetItem(line)
            item.setToolTip(line)
            item.setBackground(QBrush(NAME_CHANGE_COLOR))
            item.setForeground(QBrush(QColor("#202020")))
            self.name_table.setItem(row_idx, 0, item)

    def _selected_name_row(self):
        index = self.name_table.currentRow()
        rows = getattr(self, "_name_rows", [])
        return rows[index] if 0 <= index < len(rows) else None

    def _on_add_name_change(self) -> None:
        field = TRACKED_NAME_FIELDS[0]
        dialog = NameChangeDialog(self, tr(f"label.{field}_field"), new_value=self.member.family_name)
        if dialog.exec():
            values = dialog.values()
            add_name_change(self.conn, self.member.id, field, values["old_value"], values["new_value"], values["date"])
            self._refresh_name_history()

    def _on_name_double_click(self, index) -> None:
        rows = getattr(self, "_name_rows", [])
        if index.row() >= len(rows):
            return
        row = rows[index.row()]
        dialog = NameChangeDialog(
            self,
            tr(f"label.{row['field']}_field"),
            old_value=row["old_value"] or "",
            new_value=row["new_value"],
            date=QDate.fromString(row["changed_at"][:10], "yyyy-MM-dd"),
        )
        if dialog.exec():
            values = dialog.values()
            update_name_change(self.conn, row["id"], values["old_value"], values["new_value"], values["date"])
            self._refresh_name_history()

    def _on_delete_name_change(self) -> None:
        row = self._selected_name_row()
        if row is not None:
            delete_name_change(self.conn, row["id"])
            self._refresh_name_history()

    def _fit_history_rows(self) -> None:
        """Adatta l'altezza di ogni riga al testo mandato a capo, ma con un tetto: una
        nota molto lunga faceva diventare la riga altissima. Oltre il tetto la riga
        resta compatta (2-3 righe) e il testo intero è comunque nel tooltip. Va rifatto
        quando cambia la larghezza della tabella: alla prima apertura la tabella non
        ha ancora la larghezza definitiva e le righe uscivano troppo alte."""
        if not self._history_rows:
            return
        self.history_table.resizeRowsToContents()
        for row_idx in range(self.history_table.rowCount()):
            if self.history_table.rowHeight(row_idx) > MAX_HISTORY_ROW_HEIGHT:
                self.history_table.setRowHeight(row_idx, MAX_HISTORY_ROW_HEIGHT)

    def eventFilter(self, obj, event) -> bool:
        if (
            event.type() == QEvent.Resize
            and getattr(self, "history_table", None) is not None
            and obj is self.history_table.viewport()
        ):
            # Differito: nel momento dell'evento la colonna non ha ancora la larghezza nuova.
            QTimer.singleShot(0, self._fit_history_rows)
        return super().eventFilter(obj, event)

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

    def _on_rebuild_history(self) -> None:
        dialog = RebuildHistoryDialog(self, self.member, self._history_rows)
        if dialog.exec():
            rebuild_status_history(self.conn, self.member.id, dialog.entries())
            self.history_changed = True
            self._refresh_history()
            # Il primo passaggio ricostruito è il nuovo ingresso in gilda: riflettilo nel form.
            first_entry = dialog.entries()[0]
            self.date_check.setChecked(True)
            self.date_picker.setDate(QDate.fromString(first_entry["date"], "yyyy-MM-dd"))

    def validate(self) -> bool:
        if not self.family_edit.text().strip():
            self.error_label.setText(tr("error.family_name_required"))
            self.error_label.show()
            self._fit_scroll_height()
            self._scroll.ensureWidgetVisible(self.error_label)
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
