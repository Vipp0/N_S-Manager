from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    CheckBox,
    ComboBox,
    FluentIcon as FIF,
    LineEdit,
    MessageBoxBase,
    PushButton,
    ScrollArea,
    SubtitleLabel,
    TransparentToolButton,
)

from gilda_app.i18n import tr
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO, status_label
from gilda_app.ui.fast_calendar_picker import DateEdit

ALL_STATUSES = [STATUS_ATTIVO, STATUS_EX_MEMBRO, STATUS_BANNATO]


class _HistoryRow(QWidget):
    """Un passaggio della sequenza: numero d'ordine, lista di destinazione, data (o
    "sconosciuta") e nota opzionale, con i pulsanti per spostarlo ed eliminarlo."""

    remove_requested = Signal(object)
    move_requested = Signal(object, int)

    def __init__(self, parent, status: str, date: QDate | None, note: str | None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.number_label = QLabel("", self)
        self.number_label.setFixedWidth(26)

        self.status_combo = ComboBox(self)
        for st in ALL_STATUSES:
            self.status_combo.addItem(status_label(st), userData=st)
        self.status_combo.setCurrentIndex(self.status_combo.findData(status))
        self.status_combo.setFixedWidth(150)

        self.date_edit = DateEdit(self)
        self.date_edit.setDate(date or QDate.currentDate())
        self.date_edit.setFixedWidth(150)

        self.unknown_check = CheckBox(tr("rebuild.unknown_short"), self)
        self.unknown_check.setToolTip(tr("label.unknown_date"))
        self.unknown_check.toggled.connect(lambda unknown: self.date_edit.setEnabled(not unknown))
        self.unknown_check.setChecked(date is None)

        self.note_edit = LineEdit(self)
        self.note_edit.setPlaceholderText(tr("field.note.placeholder"))
        if note:
            self.note_edit.setText(note)

        self.up_btn = TransparentToolButton(FIF.UP, self)
        self.up_btn.setToolTip(tr("dialog.rebuild_history.move_up"))
        self.up_btn.clicked.connect(lambda: self.move_requested.emit(self, -1))
        self.down_btn = TransparentToolButton(FIF.DOWN, self)
        self.down_btn.setToolTip(tr("dialog.rebuild_history.move_down"))
        self.down_btn.clicked.connect(lambda: self.move_requested.emit(self, 1))
        self.remove_btn = TransparentToolButton(FIF.DELETE, self)
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        for button in (self.up_btn, self.down_btn, self.remove_btn):
            button.setFixedWidth(32)

        layout.addWidget(self.number_label)
        layout.addWidget(self.status_combo)
        layout.addWidget(self.date_edit)
        layout.addWidget(self.unknown_check)
        layout.addWidget(self.note_edit, 1)
        layout.addWidget(self.up_btn)
        layout.addWidget(self.down_btn)
        layout.addWidget(self.remove_btn)

    def set_position(self, number: int, is_first: bool, is_last: bool) -> None:
        self.number_label.setText(f"{number}.")
        self.up_btn.setEnabled(not is_first)
        self.down_btn.setEnabled(not is_last)

    def status(self) -> str:
        return self.status_combo.currentData()

    def date(self) -> QDate | None:
        return None if self.unknown_check.isChecked() else self.date_edit.getDate()

    def note(self) -> str | None:
        return self.note_edit.text().strip() or None


class RebuildHistoryDialog(MessageBoxBase):
    """Ricostruisce da zero lo storico movimenti di un membro: utile per inserire a
    posteriori entrate/uscite/rientri già avvenuti (es. dopo l'import di un database
    che non aveva ancora questo tracciamento), invece di doverli rifare uno alla volta
    con "sposta" scegliendo ogni volta una data nel passato. I passaggi restano
    nell'ordine mostrato, così si possono inserire anche quelli di cui non si conosce la
    data, o due passaggi consecutivi nella stessa lista quando ne manca uno: in questi casi
    si riceve un avviso, ma si può confermare comunque. Una volta ricostruito, i comandi
    normali (sposta, correggi voce) proseguono da qui in avanti come al solito.
    """

    def __init__(self, parent, member, history_rows):
        super().__init__(parent)
        self.member = member
        self._rows: list[_HistoryRow] = []
        self._entries: list[dict] = []
        self._confirmed_signature = None

        self.titleLabel = SubtitleLabel(tr("dialog.rebuild_history.title", name=member.family_name), self)
        self.viewLayout.addWidget(self.titleLabel)

        hint = QLabel(tr("dialog.rebuild_history.hint"), self)
        hint.setWordWrap(True)
        self.viewLayout.addWidget(hint)

        self._rows_widget = QWidget(self)
        self._rows_widget.setObjectName("rebuildHistoryRows")
        self._rows_widget.setStyleSheet("#rebuildHistoryRows { background: transparent; }")
        self._rows_layout = QVBoxLayout(self._rows_widget)
        self._rows_layout.setContentsMargins(0, 0, 12, 0)
        self._rows_layout.setSpacing(8)
        self._rows_layout.addStretch(1)
        self._scroll = ScrollArea(self)
        self._scroll.setWidget(self._rows_widget)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.enableTransparentBackground()
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setFixedHeight(240)
        self.viewLayout.addWidget(self._scroll)

        buttons = QHBoxLayout()
        self.add_btn = PushButton(FIF.ADD, tr("dialog.rebuild_history.add_row"), self)
        self.add_btn.clicked.connect(lambda: self._add_row())
        self.sort_btn = PushButton(FIF.SYNC, tr("dialog.rebuild_history.sort"), self)
        self.sort_btn.clicked.connect(self._sort_by_date)
        buttons.addWidget(self.add_btn)
        buttons.addWidget(self.sort_btn)
        buttons.addStretch(1)
        self.viewLayout.addLayout(buttons)

        self.error_label = QLabel(self)
        self.error_label.setStyleSheet("color: #b45309;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        self.viewLayout.addWidget(self.error_label)

        if history_rows:
            for row in history_rows:
                self._add_row(
                    status=row["new_status"],
                    date=QDate.fromString(row["changed_at"][:10], "yyyy-MM-dd") if row["changed_at"] else None,
                    note=row["note"],
                    unknown=row["changed_at"] is None,
                )
        else:
            self._add_row()

        self.widget.setMinimumWidth(840)
        self.yesButton.setText(tr("button.save"))
        self.cancelButton.setText(tr("button.cancel"))

    # -- righe ------------------------------------------------------------
    def _add_row(
        self, status: str | None = None, date: QDate | None = None, note: str | None = None, unknown: bool = False
    ) -> None:
        row_date = None if unknown else (date or QDate.currentDate())
        row = _HistoryRow(self._rows_widget, status or STATUS_ATTIVO, row_date, note)
        row.remove_requested.connect(self._remove_row)
        row.move_requested.connect(self._move_row)
        self._rows.append(row)
        self._reflow_rows()

    def _reflow_rows(self) -> None:
        """Rimette i widget nel layout secondo l'ordine di self._rows e aggiorna i numeri."""
        for row in self._rows:
            self._rows_layout.removeWidget(row)
        for index, row in enumerate(self._rows):
            self._rows_layout.insertWidget(index, row)
            row.set_position(index + 1, index == 0, index == len(self._rows) - 1)

    def _remove_row(self, row: _HistoryRow) -> None:
        # Almeno un passaggio deve restare: uno storico vuoto non ha senso.
        if len(self._rows) <= 1:
            return
        self._rows.remove(row)
        self._rows_layout.removeWidget(row)
        row.deleteLater()
        self._reflow_rows()

    def _move_row(self, row: _HistoryRow, delta: int) -> None:
        index = self._rows.index(row)
        target = index + delta
        if 0 <= target < len(self._rows):
            self._rows[index], self._rows[target] = self._rows[target], self._rows[index]
            self._reflow_rows()

    def _sort_by_date(self) -> None:
        """Ordina per data; un passaggio a data sconosciuta resta subito dopo quello che lo
        precede (eredita la sua data), così non cambia posizione rispetto ai vicini."""
        keyed = []
        carry = None
        for index, row in enumerate(self._rows):
            date = row.date()
            if date is not None:
                carry = date.toJulianDay()
            keyed.append((carry if carry is not None else -1, index, row))
        self._rows = [row for _, _, row in sorted(keyed, key=lambda item: (item[0], item[1]))]
        self._reflow_rows()

    # -- conferma ------------------------------------------------------------
    def _warnings(self) -> list[str]:
        messages = []
        repeated = [
            f"{i + 1}-{i + 2}" for i in range(len(self._rows) - 1) if self._rows[i].status() == self._rows[i + 1].status()
        ]
        if repeated:
            messages.append(tr("dialog.rebuild_history.warn_same_status", rows=", ".join(repeated)))
        out_of_order = []
        last_known = None
        for index, row in enumerate(self._rows):
            date = row.date()
            if date is None:
                continue
            if last_known is not None and date < last_known:
                out_of_order.append(str(index + 1))
            last_known = date
        if out_of_order:
            messages.append(tr("dialog.rebuild_history.warn_order", rows=", ".join(out_of_order)))
        return messages

    def validate(self) -> bool:
        """Gli avvisi non bloccano: al primo Salva si mostrano, se non si cambia nulla il
        secondo Salva conferma comunque."""
        signature = tuple(
            (row.status(), row.date().toString("yyyy-MM-dd") if row.date() else None, row.note()) for row in self._rows
        )
        warnings = self._warnings()
        if warnings and signature != self._confirmed_signature:
            self._confirmed_signature = signature
            self.error_label.setText("\n".join(warnings))
            self.error_label.show()
            return False
        self.error_label.hide()
        self._entries = [
            {"status": row.status(), "date": row.date(), "note": row.note()} for row in self._rows
        ]
        return True

    def entries(self) -> list[dict]:
        """Sequenza nell'ordine mostrato, pronta per rebuild_status_history(); valida solo
        dopo un validate() riuscito (chiamato automaticamente da exec() alla conferma)."""
        return [
            {"status": e["status"], "date": e["date"].toString("yyyy-MM-dd") if e["date"] else None, "note": e["note"]}
            for e in self._entries
        ]
