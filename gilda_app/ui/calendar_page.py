from datetime import date, timedelta

from PySide6.QtCore import QDate, QLocale, Qt
from PySide6.QtWidgets import QCalendarWidget, QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import MessageBox, PrimaryPushButton, PushButton, StrongBodyLabel, SubtitleLabel, TransparentToolButton

from gilda_app.db.calendar_events import (
    RECURRENCE_DAILY,
    RECURRENCE_NONE,
    RECURRENCE_WEEKLY,
    add_event,
    delete_event,
    get_all_events,
    occurrences_in_range,
    update_event,
)
from gilda_app.i18n import get_language, tr
from gilda_app.ui.calendar_event_dialog import CalendarEventDialog
from gilda_app.ui.event_calendar_widget import EventCalendarWidget
from gilda_app.utils.date_format import DISPLAY_DATE_QT_FORMAT

_UNIT_LABEL_KEYS = {
    RECURRENCE_DAILY: "calendar.unit.days",
    RECURRENCE_WEEKLY: "calendar.unit.weeks",
    "monthly": "calendar.unit.months",
}


class CalendarPage(QWidget):
    """Calendario mensile degli eventi della gilda. A sinistra il mese (i giorni con
    eventi sono colorati a fasce, una per evento), a destra l'elenco
    degli eventi del giorno selezionato con aggiunta/modifica/eliminazione."""

    def __init__(self, get_conn, parent=None):
        super().__init__(parent)
        self.get_conn = get_conn
        self._day_events: dict[date, list] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)

        left = QVBoxLayout()
        title_row = QHBoxLayout()
        title_row.addWidget(SubtitleLabel(tr("nav.calendar"), self))
        title_row.addStretch(1)
        today_btn = PushButton(FIF.CALENDAR, tr("calendar.today"), self)
        today_btn.clicked.connect(self._go_to_today)
        title_row.addWidget(today_btn)
        left.addLayout(title_row)
        self.calendar = EventCalendarWidget(self)
        self.calendar.setLocale(QLocale(QLocale.Italian if get_language() == "it" else QLocale.English))
        self.calendar.setFirstDayOfWeek(Qt.Monday)
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.setMinimumSize(640, 480)
        self.calendar.selectionChanged.connect(self._refresh_day_panel)
        # activated = doppio click (o Invio) su un giorno: apre subito il form di
        # aggiunta evento su quella data.
        self.calendar.activated.connect(lambda _date: self._on_add())
        self.calendar.currentPageChanged.connect(lambda *_: self._refresh_month_formats())
        left.addWidget(self.calendar, 1)
        layout.addLayout(left, 3)

        right = QVBoxLayout()
        right.setSpacing(10)
        self.day_title = StrongBodyLabel("", self)
        right.addWidget(self.day_title)
        add_btn = PrimaryPushButton(FIF.ADD, tr("calendar.add"), self)
        add_btn.clicked.connect(self._on_add)
        right.addWidget(add_btn)

        self.events_container = QWidget()
        self.events_layout = QVBoxLayout(self.events_container)
        self.events_layout.setContentsMargins(0, 0, 0, 0)
        self.events_layout.setSpacing(8)
        self.events_layout.addStretch(1)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(self.events_container)
        right.addWidget(scroll, 1)
        layout.addLayout(right, 2)

        self.refresh()

    # -- dati -----------------------------------------------------------
    def refresh(self) -> None:
        self._refresh_month_formats()
        self._refresh_day_panel()

    def _refresh_month_formats(self) -> None:
        """Ricalcola gli eventi visibili e colora i giorni che ne hanno."""
        first = date(self.calendar.yearShown(), self.calendar.monthShown(), 1)
        # Margine di una settimana: la griglia mostra anche i giorni dei mesi vicini.
        range_start = first - timedelta(days=7)
        next_month = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
        range_end = next_month + timedelta(days=7)

        self._day_events = {}
        for row in get_all_events(self.get_conn()):
            for occurrence in occurrences_in_range(row, range_start, range_end):
                self._day_events.setdefault(occurrence, []).append(row)

        self.calendar.set_day_events(
            {day: [(row["title"], row["color"]) for row in rows] for day, rows in self._day_events.items()}
        )

    def _go_to_today(self) -> None:
        today = QDate.currentDate()
        self.calendar.setSelectedDate(today)
        self.calendar.setCurrentPage(today.year(), today.month())

    def _selected_date(self) -> date:
        qd = self.calendar.selectedDate()
        return date(qd.year(), qd.month(), qd.day())

    # -- pannello del giorno ---------------------------------------------
    def _refresh_day_panel(self) -> None:
        selected = self.calendar.selectedDate()
        self.day_title.setText(selected.toString(DISPLAY_DATE_QT_FORMAT))

        while self.events_layout.count() > 1:
            item = self.events_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        rows = self._day_events.get(self._selected_date(), [])
        if not rows:
            self.events_layout.insertWidget(0, QLabel(tr("calendar.no_events"), self.events_container))
            return
        for index, row in enumerate(rows):
            self.events_layout.insertWidget(index, self._event_row(row))

    def _event_row(self, row) -> QWidget:
        frame = QFrame(self.events_container)
        frame.setFrameShape(QFrame.StyledPanel)
        outer = QHBoxLayout(frame)
        outer.setContentsMargins(10, 8, 8, 8)

        dot = QLabel(frame)
        dot.setFixedSize(14, 14)
        dot.setStyleSheet(f"background-color: {row['color']}; border-radius: 7px;")
        outer.addWidget(dot, 0, Qt.AlignTop)

        text_col = QVBoxLayout()
        title = StrongBodyLabel(row["title"], frame)
        title.setWordWrap(True)
        text_col.addWidget(title)
        if row["recurrence_unit"] != RECURRENCE_NONE:
            hint = tr(
                "calendar.recurring_hint",
                n=row["recurrence_interval"],
                unit=tr(_UNIT_LABEL_KEYS[row["recurrence_unit"]]),
            )
            text_col.addWidget(QLabel(hint, frame))
        if row["note"]:
            note = QLabel(row["note"], frame)
            note.setWordWrap(True)
            text_col.addWidget(note)
        outer.addLayout(text_col, 1)

        edit_btn = TransparentToolButton(FIF.EDIT, frame)
        edit_btn.setToolTip(tr("menu.edit"))
        edit_btn.clicked.connect(lambda _=False, r=row: self._on_edit(r))
        delete_btn = TransparentToolButton(FIF.DELETE, frame)
        delete_btn.setToolTip(tr("menu.delete"))
        delete_btn.clicked.connect(lambda _=False, r=row: self._on_delete(r))
        outer.addWidget(edit_btn, 0, Qt.AlignTop)
        outer.addWidget(delete_btn, 0, Qt.AlignTop)
        return frame

    # -- azioni -----------------------------------------------------------
    def _on_add(self) -> None:
        dialog = CalendarEventDialog(self.window(), start_date=self.calendar.selectedDate())
        if dialog.exec():
            add_event(self.get_conn(), **dialog.values())
            self.refresh()

    def _on_edit(self, row) -> None:
        dialog = CalendarEventDialog(self.window(), event=row)
        if dialog.exec():
            update_event(self.get_conn(), row["id"], **dialog.values())
            self.refresh()

    def _on_delete(self, row) -> None:
        body_key = "calendar.delete.body_series" if row["recurrence_unit"] != RECURRENCE_NONE else "calendar.delete.body"
        box = MessageBox(tr("calendar.delete.title"), tr(body_key, title=row["title"]), self.window())
        if box.exec():
            delete_event(self.get_conn(), row["id"])
            self.refresh()
