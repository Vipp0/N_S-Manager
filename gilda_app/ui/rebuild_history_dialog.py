from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
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
    """Un passaggio della sequenza: lista di destinazione + data + nota opzionale."""

    remove_requested = Signal(object)

    def __init__(self, parent, status: str, date: QDate, note: str | None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.status_combo = ComboBox(self)
        for st in ALL_STATUSES:
            self.status_combo.addItem(status_label(st), userData=st)
        self.status_combo.setCurrentIndex(self.status_combo.findData(status))
        self.status_combo.setFixedWidth(150)

        self.date_edit = DateEdit(self)
        self.date_edit.setDate(date)
        self.date_edit.setFixedWidth(150)

        self.note_edit = LineEdit(self)
        self.note_edit.setPlaceholderText(tr("field.note.placeholder"))
        if note:
            self.note_edit.setText(note)

        self.remove_btn = TransparentToolButton(FIF.DELETE, self)
        self.remove_btn.setFixedWidth(32)
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))

        layout.addWidget(self.status_combo)
        layout.addWidget(self.date_edit)
        layout.addWidget(self.note_edit, 1)
        layout.addWidget(self.remove_btn)

    def status(self) -> str:
        return self.status_combo.currentData()

    def date(self) -> QDate:
        return self.date_edit.getDate()

    def note(self) -> str | None:
        return self.note_edit.text().strip() or None


class RebuildHistoryDialog(MessageBoxBase):
    """Ricostruisce da zero lo storico movimenti di un membro: utile per inserire a
    posteriori entrate/uscite/rientri già avvenuti (es. dopo l'import di un database
    che non aveva ancora questo tracciamento), invece di doverli rifare uno alla volta
    con "sposta" scegliendo ogni volta una data nel passato. Una volta ricostruito, i
    comandi normali (sposta, correggi voce) proseguono da qui in avanti come al solito.
    """

    def __init__(self, parent, member, history_rows):
        super().__init__(parent)
        self.member = member
        self._rows: list[_HistoryRow] = []
        self._entries: list[dict] = []

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
        self._scroll = ScrollArea(self)
        self._scroll.setWidget(self._rows_widget)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.enableTransparentBackground()
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setFixedHeight(220)
        self.viewLayout.addWidget(self._scroll)

        self.add_btn = PushButton(FIF.ADD, tr("dialog.rebuild_history.add_row"), self)
        self.add_btn.clicked.connect(lambda: self._add_row())
        self.viewLayout.addWidget(self.add_btn)

        self.error_label = QLabel(self)
        self.error_label.setStyleSheet("color: #c42b1c;")
        self.error_label.hide()
        self.viewLayout.addWidget(self.error_label)

        if history_rows:
            for row in history_rows:
                self._add_row(
                    status=row["new_status"],
                    date=QDate.fromString(row["changed_at"][:10], "yyyy-MM-dd"),
                    note=row["note"],
                )
        else:
            self._add_row()

        self.widget.setMinimumWidth(560)
        self.yesButton.setText(tr("button.save"))
        self.cancelButton.setText(tr("button.cancel"))

    def _add_row(self, status: str | None = None, date: QDate | None = None, note: str | None = None) -> None:
        row = _HistoryRow(self._rows_widget, status or STATUS_ATTIVO, date or QDate.currentDate(), note)
        row.remove_requested.connect(self._remove_row)
        self._rows_layout.addWidget(row)
        self._rows.append(row)

    def _remove_row(self, row: _HistoryRow) -> None:
        # Almeno un passaggio deve restare: uno storico vuoto non ha senso.
        if len(self._rows) <= 1:
            return
        self._rows.remove(row)
        self._rows_layout.removeWidget(row)
        row.deleteLater()

    def validate(self) -> bool:
        entries = sorted(
            ({"status": r.status(), "date": r.date(), "note": r.note()} for r in self._rows),
            key=lambda e: e["date"],
        )
        for prev, curr in zip(entries, entries[1:]):
            if prev["status"] == curr["status"]:
                self.error_label.setText(tr("dialog.rebuild_history.error_same_status"))
                self.error_label.show()
                return False
        self.error_label.hide()
        self._entries = entries
        return True

    def entries(self) -> list[dict]:
        """Sequenza cronologica pronta per rebuild_status_history(); valida solo dopo
        un validate() riuscito (chiamato automaticamente da exec() alla conferma)."""
        return [
            {"status": e["status"], "date": e["date"].toString("yyyy-MM-dd"), "note": e["note"]}
            for e in self._entries
        ]
