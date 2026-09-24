from PySide6.QtCore import QLocale, Qt
from PySide6.QtWidgets import QCompleter, QHBoxLayout, QWidget
from qfluentwidgets import EditableComboBox, LineEdit, SpinBox
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets.components.widgets.spin_box import SpinButton

from gilda_app.i18n import get_language, tr
from gilda_app.utils.birthday import build_birthday, split_birthday

BUTTON_TEXT_MARGIN = 36


class _DaySpinBox(SpinBox):
    """Giorno 1-31 con freccia sinistra che scende e destra che sale. Le frecce non si
    fermano agli estremi: da 31 si riparte da 1 e da 1 si torna a 31, senza passare per
    il valore vuoto (0), che resta raggiungibile solo scrivendolo a mano."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0, 31)
        self.setSpecialValueText("—")  # 0 = non indicato
        # Sostituisce le due frecce impilate a destra con una a ciascun lato.
        self.upButton.hide()
        self.downButton.hide()
        self._minus = SpinButton(FIF.CARE_LEFT_SOLID, self)
        self._plus = SpinButton(FIF.CARE_RIGHT_SOLID, self)
        layout = self.hBoxLayout
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setAlignment(Qt.AlignVCenter)
        layout.addWidget(self._minus, 0, Qt.AlignLeft)
        layout.addStretch(1)
        layout.addWidget(self._plus, 0, Qt.AlignRight)
        self._minus.clicked.connect(self.stepDown)
        self._plus.clicked.connect(self.stepUp)
        self.lineEdit().setAlignment(Qt.AlignCenter)
        self.lineEdit().setTextMargins(BUTTON_TEXT_MARGIN, 0, BUTTON_TEXT_MARGIN, 0)

    def stepBy(self, steps: int) -> None:
        new = self.value() + steps
        if new > 31:
            new = 1
        elif new < 1:
            new = 31
        self.setValue(new)


class BirthdayEdit(QWidget):
    """Giorno + mese (menù a tendina scrivibile, con completamento) + anno facoltativo.
    Tutto vuoto = nessun compleanno registrato."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.day_spin = _DaySpinBox(self)
        self.day_spin.setFixedWidth(128)

        locale = QLocale(QLocale.Italian if get_language() == "it" else QLocale.English)
        self._month_names = [locale.monthName(month) for month in range(1, 13)]
        self.month_combo = EditableComboBox(self)
        self.month_combo.setPlaceholderText(tr("birthday.month_placeholder"))
        self.month_combo.addItems(self._month_names)
        # addItems seleziona il primo elemento: si parte dal campo vuoto.
        self.month_combo.setCurrentIndex(-1)
        completer = QCompleter(self._month_names, self.month_combo)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchStartsWith)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self.month_combo.setCompleter(completer)
        self.month_combo.setMinimumWidth(0)

        self.year_edit = LineEdit(self)
        self.year_edit.setPlaceholderText(tr("birthday.year_placeholder"))
        self.year_edit.setToolTip(tr("birthday.year_tooltip"))
        self.year_edit.setMaxLength(4)
        self.year_edit.setFixedWidth(120)

        layout.addWidget(self.day_spin)
        layout.addWidget(self.month_combo, 1)
        layout.addWidget(self.year_edit)

    def _parse_month(self) -> int:
        """Mese scritto o scelto: nome intero, inizio del nome (se univoco) oppure numero
        1-12. 0 se vuoto, ValueError se non riconoscibile."""
        text = self.month_combo.text().strip().casefold()
        if not text:
            return 0
        names = [name.casefold() for name in self._month_names]
        if text in names:
            return names.index(text) + 1
        matches = [i for i, name in enumerate(names) if name.startswith(text)]
        if len(matches) == 1:
            return matches[0] + 1
        if text.isdigit() and 1 <= int(text) <= 12:
            return int(text)
        raise ValueError("unrecognized month")

    def set_value(self, value: str | None) -> None:
        parts = split_birthday(value)
        if parts is None:
            self.day_spin.setValue(0)
            self.month_combo.setText("")
            self.year_edit.clear()
            return
        day, month, year = parts
        self.day_spin.setValue(day)
        self.month_combo.setText(self._month_names[month - 1] if 1 <= month <= 12 else "")
        self.year_edit.setText(str(year) if year else "")

    def value(self) -> str | None:
        """Valore da salvare, None se vuoto. ValueError se incompleto o non valido."""
        return build_birthday(self.day_spin.value(), self._parse_month(), self.year_edit.text())
