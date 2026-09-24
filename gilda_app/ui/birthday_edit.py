from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QHBoxLayout, QWidget
from qfluentwidgets import ComboBox, LineEdit, SpinBox

from gilda_app.i18n import get_language, tr
from gilda_app.utils.birthday import build_birthday, split_birthday


class BirthdayEdit(QWidget):
    """Giorno + mese + anno facoltativo. Tutto vuoto = nessun compleanno registrato."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.day_spin = SpinBox(self)
        self.day_spin.setRange(0, 31)
        self.day_spin.setSpecialValueText("—")  # 0 = non indicato
        self.day_spin.setFixedWidth(136)  # le frecce dello spinbox occupano molto: con meno spazio il numero si taglia

        locale = QLocale(QLocale.Italian if get_language() == "it" else QLocale.English)
        self.month_combo = ComboBox(self)
        self.month_combo.addItem("—", userData=0)
        for month in range(1, 13):
            self.month_combo.addItem(locale.monthName(month), userData=month)

        self.year_edit = LineEdit(self)
        self.year_edit.setPlaceholderText(tr("birthday.year_placeholder"))
        self.year_edit.setMaxLength(4)
        self.year_edit.setFixedWidth(90)

        layout.addWidget(self.day_spin)
        self.month_combo.setMinimumWidth(0)
        layout.addWidget(self.month_combo, 1)
        layout.addWidget(self.year_edit)

    def set_value(self, value: str | None) -> None:
        parts = split_birthday(value)
        if parts is None:
            self.day_spin.setValue(0)
            self.month_combo.setCurrentIndex(0)
            self.year_edit.clear()
            return
        day, month, year = parts
        self.day_spin.setValue(day)
        self.month_combo.setCurrentIndex(max(0, self.month_combo.findData(month)))
        self.year_edit.setText(str(year) if year else "")

    def value(self) -> str | None:
        """Valore da salvare, None se vuoto. ValueError se incompleto o non valido."""
        return build_birthday(self.day_spin.value(), self.month_combo.currentData() or 0, self.year_edit.text())
