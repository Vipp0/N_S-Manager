from PySide6.QtCore import QDate
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget
from qfluentwidgets import (
    CheckBox,
    ComboBox,
    LineEdit,
    MessageBoxBase,
    PlainTextEdit,
    SpinBox,
    SubtitleLabel,
)

from gilda_app.db.calendar_events import (
    RECURRENCE_DAILY,
    RECURRENCE_MONTHLY,
    RECURRENCE_NONE,
    RECURRENCE_WEEKLY,
)
from gilda_app.i18n import tr
from gilda_app.ui.color_swatch_picker import ColorSwatchPicker
from gilda_app.ui.dialog_drag import make_draggable
from gilda_app.ui.fast_calendar_picker import DateEdit
# Etichetta dell'unità nel campo "ogni N ...", per ciascuna ricorrenza.
_UNIT_LABEL_KEYS = {
    RECURRENCE_DAILY: "calendar.unit.days",
    RECURRENCE_WEEKLY: "calendar.unit.weeks",
    RECURRENCE_MONTHLY: "calendar.unit.months",
}


class CalendarEventDialog(MessageBoxBase):
    """Form per aggiungere o modificare un evento del calendario (anche ricorrente)."""

    def __init__(self, parent, event=None, start_date: QDate | None = None, duplicate_of=None):
        """event: evento da modificare. duplicate_of: evento da cui partire per crearne uno
        nuovo (titolo, nota, colore e ricorrenza già compilati, data a scelta)."""
        super().__init__(parent)
        is_edit = event is not None
        source = event if is_edit else duplicate_of

        if is_edit:
            title_key = "calendar.dialog.edit"
        else:
            title_key = "calendar.dialog.duplicate" if duplicate_of is not None else "calendar.dialog.new"
        self.titleLabel = SubtitleLabel(tr(title_key), self)
        self.viewLayout.addWidget(self.titleLabel)

        self.title_edit = LineEdit(self)
        self.title_edit.setPlaceholderText(tr("calendar.field.title"))
        self.viewLayout.addWidget(QLabel(tr("calendar.field.title"), self))
        self.viewLayout.addWidget(self.title_edit)

        self.date_picker = DateEdit(self)
        self.date_picker.setDate(start_date or QDate.currentDate())
        self.viewLayout.addWidget(QLabel(tr("calendar.field.date"), self))
        self.viewLayout.addWidget(self.date_picker)

        self.color_picker = ColorSwatchPicker(self)
        self.viewLayout.addWidget(QLabel(tr("calendar.field.color"), self))
        self.viewLayout.addWidget(self.color_picker)

        self.note_edit = PlainTextEdit(self)
        self.note_edit.setPlaceholderText(tr("calendar.field.note"))
        self.note_edit.setFixedHeight(80)
        self.viewLayout.addWidget(QLabel(tr("calendar.field.note"), self))
        self.viewLayout.addWidget(self.note_edit)

        # Ricorrenza: tipo + "ogni N", e scadenza opzionale (stesso schema
        # casella + data usato in MemberDialog per la data di ingresso).
        self.viewLayout.addWidget(QLabel(tr("calendar.field.repeat"), self))
        self.recurrence_combo = ComboBox(self)
        self.recurrence_combo.addItem(tr("calendar.repeat.none"), userData=RECURRENCE_NONE)
        self.recurrence_combo.addItem(tr("calendar.repeat.daily"), userData=RECURRENCE_DAILY)
        self.recurrence_combo.addItem(tr("calendar.repeat.weekly"), userData=RECURRENCE_WEEKLY)
        self.recurrence_combo.addItem(tr("calendar.repeat.monthly"), userData=RECURRENCE_MONTHLY)
        self.viewLayout.addWidget(self.recurrence_combo)

        self.interval_row = QWidget(self)
        interval_layout = QHBoxLayout(self.interval_row)
        interval_layout.setContentsMargins(0, 0, 0, 0)
        interval_layout.addWidget(QLabel(tr("calendar.field.every"), self.interval_row))
        self.interval_spin = SpinBox(self.interval_row)
        self.interval_spin.setRange(1, 365)
        interval_layout.addWidget(self.interval_spin)
        self.unit_label = QLabel("", self.interval_row)
        interval_layout.addWidget(self.unit_label)
        interval_layout.addStretch(1)
        self.viewLayout.addWidget(self.interval_row)

        self.end_check = CheckBox(tr("calendar.field.end_check"), self)
        self.end_picker = DateEdit(self)
        self.end_picker.setDate(QDate.currentDate())
        self.end_picker.setEnabled(False)
        self.end_check.toggled.connect(self.end_picker.setEnabled)
        self.end_row = QWidget(self)
        end_layout = QHBoxLayout(self.end_row)
        end_layout.setContentsMargins(0, 0, 0, 0)
        end_layout.addWidget(self.end_check)
        end_layout.addWidget(self.end_picker)
        self.viewLayout.addWidget(self.end_row)

        self.error_label = QLabel(self)
        self.error_label.setStyleSheet("color: #c42b1c;")
        self.error_label.hide()
        self.viewLayout.addWidget(self.error_label)

        self.recurrence_combo.currentIndexChanged.connect(self._update_recurrence_widgets)

        if source is not None:
            self.title_edit.setText(source["title"])
            if is_edit:  # in duplicazione la data resta quella scelta (start_date): è ciò che si cambia
                self.date_picker.setDate(QDate.fromString(source["start_date"], "yyyy-MM-dd"))
            self.color_picker.setColor(source["color"])
            if source["note"]:
                self.note_edit.setPlainText(source["note"])
            self.recurrence_combo.setCurrentIndex(self.recurrence_combo.findData(source["recurrence_unit"]))
            self.interval_spin.setValue(source["recurrence_interval"])
            if source["recurrence_end_date"]:
                self.end_check.setChecked(True)
                self.end_picker.setDate(QDate.fromString(source["recurrence_end_date"], "yyyy-MM-dd"))
        self._update_recurrence_widgets()

        # 580 invece di 500: con 15 colori (invece dei precedenti 11) la fila di pallini
        # è più larga e usciva dai bordi.
        self.widget.setMinimumWidth(580)
        self.yesButton.setText(tr("button.save"))
        self.cancelButton.setText(tr("button.cancel"))
        make_draggable(self, self.titleLabel)

    def _recurrence_unit(self) -> str:
        return self.recurrence_combo.currentData()

    def _update_recurrence_widgets(self) -> None:
        unit = self._recurrence_unit()
        repeats = unit != RECURRENCE_NONE
        self.interval_row.setVisible(repeats)
        self.end_row.setVisible(repeats)
        if repeats:
            self.unit_label.setText(tr(_UNIT_LABEL_KEYS[unit]))

    def validate(self) -> bool:
        if not self.title_edit.text().strip():
            self.error_label.setText(tr("calendar.error.title_required"))
            self.error_label.show()
            return False
        if self._recurrence_unit() != RECURRENCE_NONE and self.end_check.isChecked():
            if self.end_picker.getDate() < self.date_picker.getDate():
                self.error_label.setText(tr("calendar.error.end_before_start"))
                self.error_label.show()
                return False
        return True

    def values(self) -> dict:
        unit = self._recurrence_unit()
        repeats = unit != RECURRENCE_NONE
        end_date = None
        if repeats and self.end_check.isChecked():
            end_date = self.end_picker.getDate().toString("yyyy-MM-dd")
        return {
            "start_date": self.date_picker.getDate().toString("yyyy-MM-dd"),
            "title": self.title_edit.text().strip(),
            "note": self.note_edit.toPlainText().strip() or None,
            "color": self.color_picker.color(),
            "recurrence_unit": unit,
            "recurrence_interval": self.interval_spin.value() if repeats else 1,
            "recurrence_end_date": end_date,
        }
