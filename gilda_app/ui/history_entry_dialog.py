from PySide6.QtCore import QDate
from PySide6.QtWidgets import QLabel
from qfluentwidgets import CheckBox, MessageBoxBase, PlainTextEdit, SubtitleLabel

from gilda_app.i18n import tr
from gilda_app.ui.fast_calendar_picker import DateEdit
from gilda_app.utils.history_format import format_history_line


class HistoryEntryDialog(MessageBoxBase):
    """Correzione di data/nota per una singola voce dello storico movimenti."""

    def __init__(self, parent, history_row):
        super().__init__(parent)
        self.history_row = history_row

        self.titleLabel = SubtitleLabel(tr("dialog.edit_history.title"), self)
        self.viewLayout.addWidget(self.titleLabel)
        history_label = QLabel(format_history_line(history_row), self)
        history_label.setWordWrap(True)  # le voci con nota lunga vanno a capo, non troncate
        self.viewLayout.addWidget(history_label)

        self.viewLayout.addWidget(QLabel(tr("label.date"), self))
        self.date_picker = DateEdit(self)
        changed_at = history_row["changed_at"]
        self.date_picker.setDate(QDate.fromString(changed_at[:10], "yyyy-MM-dd") if changed_at else QDate.currentDate())
        self.viewLayout.addWidget(self.date_picker)
        self.unknown_check = CheckBox(tr("label.unknown_date"), self)
        self.unknown_check.toggled.connect(lambda unknown: self.date_picker.setEnabled(not unknown))
        self.unknown_check.setChecked(changed_at is None)
        self.viewLayout.addWidget(self.unknown_check)

        self.viewLayout.addWidget(QLabel(tr("label.note"), self))
        self.note_edit = PlainTextEdit(self)
        self.note_edit.setFixedHeight(70)
        if history_row["note"]:
            self.note_edit.setPlainText(history_row["note"])
        self.viewLayout.addWidget(self.note_edit)

        self.widget.setMinimumWidth(460)
        self.yesButton.setText(tr("button.save"))
        self.cancelButton.setText(tr("button.cancel"))

    def values(self) -> dict:
        return {
            "date": None if self.unknown_check.isChecked() else self.date_picker.getDate().toString("yyyy-MM-dd"),
            "note": self.note_edit.toPlainText().strip() or None,
        }
