from PySide6.QtCore import QDate
from PySide6.QtWidgets import QLabel
from qfluentwidgets import MessageBoxBase, PlainTextEdit, SubtitleLabel

from gilda_app.i18n import tr
from gilda_app.ui.fast_calendar_picker import FastCalendarPicker
from gilda_app.utils.history_format import format_history_line


class HistoryEntryDialog(MessageBoxBase):
    """Correzione di data/nota per una singola voce dello storico movimenti."""

    def __init__(self, parent, history_row):
        super().__init__(parent)
        self.history_row = history_row

        self.titleLabel = SubtitleLabel(tr("dialog.edit_history.title"), self)
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(QLabel(format_history_line(history_row), self))

        self.viewLayout.addWidget(QLabel(tr("label.date"), self))
        self.date_picker = FastCalendarPicker(self)
        self.date_picker.setDate(QDate.fromString(history_row["changed_at"][:10], "yyyy-MM-dd"))
        self.viewLayout.addWidget(self.date_picker)

        self.viewLayout.addWidget(QLabel(tr("label.note"), self))
        self.note_edit = PlainTextEdit(self)
        self.note_edit.setFixedHeight(70)
        if history_row["note"]:
            self.note_edit.setPlainText(history_row["note"])
        self.viewLayout.addWidget(self.note_edit)

        self.widget.setMinimumWidth(340)
        self.yesButton.setText(tr("button.save"))
        self.cancelButton.setText(tr("button.cancel"))

    def values(self) -> dict:
        return {
            "date": self.date_picker.getDate().toString("yyyy-MM-dd"),
            "note": self.note_edit.toPlainText().strip() or None,
        }
