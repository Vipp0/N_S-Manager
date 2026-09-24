from PySide6.QtCore import QDate
from PySide6.QtWidgets import QLabel
from qfluentwidgets import LineEdit, MessageBoxBase, SubtitleLabel

from gilda_app.i18n import tr
from gilda_app.ui.fast_calendar_picker import DateEdit


class NameChangeDialog(MessageBoxBase):
    """Aggiunta o correzione di una voce dello storico nomi: nome precedente, nuovo nome
    e data del cambio."""

    def __init__(self, parent, field_label: str, old_value: str = "", new_value: str = "", date: QDate | None = None):
        super().__init__(parent)
        self.viewLayout.addWidget(SubtitleLabel(f"{tr('name_history.dialog_title')} — {field_label}", self))

        self.viewLayout.addWidget(QLabel(tr("label.old_name"), self))
        self.old_edit = LineEdit(self)
        self.old_edit.setText(old_value or "")
        self.viewLayout.addWidget(self.old_edit)

        self.viewLayout.addWidget(QLabel(tr("label.new_name"), self))
        self.new_edit = LineEdit(self)
        self.new_edit.setText(new_value or "")
        self.viewLayout.addWidget(self.new_edit)

        self.viewLayout.addWidget(QLabel(tr("label.date"), self))
        self.date_edit = DateEdit(self)
        self.date_edit.setDate(date or QDate.currentDate())
        self.viewLayout.addWidget(self.date_edit)

        self.error_label = QLabel(self)
        self.error_label.setStyleSheet("color: #c42b1c;")
        self.error_label.hide()
        self.viewLayout.addWidget(self.error_label)

        self.widget.setMinimumWidth(420)
        self.yesButton.setText(tr("button.save"))
        self.cancelButton.setText(tr("button.cancel"))

    def validate(self) -> bool:
        if not self.new_edit.text().strip():
            self.error_label.setText(tr("name_history.error_new_required"))
            self.error_label.show()
            return False
        return True

    def values(self) -> dict:
        return {
            "old_value": self.old_edit.text().strip() or None,
            "new_value": self.new_edit.text().strip(),
            "date": self.date_edit.getDate().toString("yyyy-MM-dd"),
        }
