from PySide6.QtCore import QLocale, Qt
from PySide6.QtWidgets import QCompleter, QHBoxLayout, QWidget
from qfluentwidgets import EditableComboBox, LineEdit, SpinBox, TransparentToolButton
from qfluentwidgets import FluentIcon as FIF

from gilda_app.i18n import get_language, tr
from gilda_app.utils.birthday import build_birthday, split_birthday

class _DaySpinBox(SpinBox):
    """Giorno con le due frecce a destra, come di consueto, ma con quella che scende a
    sinistra di quella che sale. Il ciclo passa per il valore vuoto: ... 30, 31, "—", 1, 2 ...
    così un compleanno già inserito si può anche togliere del tutto."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0, 31)
        self.setSpecialValueText("—")  # 0 = non indicato
        self.setWrapping(True)
        layout = self.hBoxLayout
        layout.removeWidget(self.upButton)
        layout.removeWidget(self.downButton)
        layout.addWidget(self.downButton, 0, Qt.AlignRight)
        layout.addWidget(self.upButton, 0, Qt.AlignRight)


class BirthdayEdit(QWidget):
    """Giorno + mese (menù a tendina scrivibile, con completamento) + anno facoltativo.
    Tutto vuoto = nessun compleanno registrato."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.day_spin = _DaySpinBox(self)
        self.day_spin.setFixedWidth(136)

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

        # Azzera giorno, mese e anno in un colpo: un compleanno inserito si può togliere.
        self.clear_btn = TransparentToolButton(FIF.CANCEL, self)
        self.clear_btn.setToolTip(tr("birthday.clear_tooltip"))
        self.clear_btn.setFixedWidth(32)
        self.clear_btn.clicked.connect(lambda: self.set_value(None))

        layout.addWidget(self.day_spin)
        layout.addWidget(self.month_combo, 1)
        layout.addWidget(self.year_edit)
        layout.addWidget(self.clear_btn)

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
