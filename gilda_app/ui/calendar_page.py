from datetime import date, timedelta

from PySide6.QtCore import QDate, QLocale, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QCalendarWidget, QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget
from qfluentwidgets import Action, InfoBar, InfoBarPosition, RoundMenu
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
    series_copy_at,
    update_event,
)
from gilda_app.db.holidays import HOLIDAY_COLOR, get_holidays_in_range
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
        # Evento copiato con "Copia evento", da incollare su un altro giorno (solo in memoria).
        self._copied_event: dict | None = None

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
        # Il giorno selezionato ha già un bordo scuro disegnato a mano in paintCell:
        # senza questo, Windows disegna sopra anche la sua barra di selezione nativa
        # (un accento verticale a sinistra della cella).
        self.calendar.setStyleSheet(
            "QCalendarWidget QAbstractItemView:enabled {"
            " selection-background-color: transparent;"
            " selection-color: black;"
            "}"
        )
        self.calendar.selectionChanged.connect(self._refresh_day_panel)
        self.calendar.day_menu_requested.connect(self._show_day_menu)
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
        self.calendar.refresh_today()
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

        for day, names in get_holidays_in_range(self.get_conn(), range_start, range_end).items():
            for name in names:
                self._day_events.setdefault(day, []).append(
                    {
                        "id": None,
                        "title": name,
                        "note": None,
                        "color": HOLIDAY_COLOR,
                        "recurrence_unit": RECURRENCE_NONE,
                        "recurrence_interval": 1,
                        "is_holiday": True,
                    }
                )

        self.calendar.set_day_events(
            {day: [(row["title"], row["color"]) for row in rows] for day, rows in self._day_events.items()}
        )

    def follow_new_day(self, previous: date, today: date) -> None:
        """Passata la mezzanotte: se il calendario era sul giorno appena finito (cioè su "oggi", come si
        apre di solito) passa al giorno nuovo, così "Aggiungi evento" non propone la data di ieri."""
        if self._selected_date() == previous:
            self.calendar.setSelectedDate(QDate(today.year, today.month, today.day))
            self.calendar.setCurrentPage(today.year, today.month)

    def _go_to_today(self) -> None:
        self.calendar.refresh_today()
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

    @staticmethod
    def _is_holiday(row) -> bool:
        return "is_holiday" in row.keys() and bool(row["is_holiday"])

    def _event_row(self, row) -> QWidget:
        frame = QFrame(self.events_container)
        frame.setFrameShape(QFrame.StyledPanel)
        if not self._is_holiday(row):
            frame.setContextMenuPolicy(Qt.CustomContextMenu)
            frame.customContextMenuRequested.connect(
                lambda pos, r=row, f=frame: self._show_event_menu(r, f.mapToGlobal(pos))
            )
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

        if not self._is_holiday(row):
            edit_btn = TransparentToolButton(FIF.EDIT, frame)
            edit_btn.setToolTip(tr("menu.edit"))
            edit_btn.clicked.connect(lambda _=False, r=row: self._on_edit(r))
            delete_btn = TransparentToolButton(FIF.DELETE, frame)
            delete_btn.setToolTip(tr("menu.delete"))
            delete_btn.clicked.connect(lambda _=False, r=row: self._on_delete(r))
            outer.addWidget(edit_btn, 0, Qt.AlignTop)
            outer.addWidget(delete_btn, 0, Qt.AlignTop)
        return frame

    def _show_event_menu(self, row, global_pos) -> None:
        menu = RoundMenu(parent=self)
        if row["note"]:
            menu.addAction(Action(FIF.COPY, tr("calendar.menu.copy_note"), triggered=lambda: self._copy(row["note"])))
            menu.addAction(
                Action(
                    FIF.COPY,
                    tr("calendar.menu.copy_title_note"),
                    triggered=lambda: self._copy(f"{row['title']}\n{row['note']}"),
                )
            )
            menu.addSeparator()
        menu.addAction(Action(FIF.COPY, tr("calendar.menu.copy_event"), triggered=lambda: self._copy_event(row)))
        menu.addAction(Action(FIF.EDIT, tr("menu.edit"), triggered=lambda: self._on_edit(row)))
        menu.addAction(Action(FIF.ADD, tr("calendar.menu.duplicate"), triggered=lambda: self._on_duplicate(row)))
        menu.addSeparator()
        menu.addAction(Action(FIF.DELETE, tr("menu.delete"), triggered=lambda: self._on_delete(row)))
        menu.exec(global_pos)

    def _toast(self, text: str) -> None:
        InfoBar.success(
            title="", content=text, isClosable=True, position=InfoBarPosition.TOP, duration=2200, parent=self.window()
        )

    def _copy(self, text: str) -> None:
        QGuiApplication.clipboard().setText(text)
        self._toast(tr("calendar.copied"))

    # -- copia / incolla di un evento tra giorni -------------------------------------
    def _copy_event(self, row) -> None:
        self._copied_event = dict(row)
        self._toast(tr("calendar.event_copied"))

    def _show_day_menu(self, day: QDate, global_pos) -> None:
        # Il giorno cliccato diventa quello selezionato: il pannello a destra mostra il suo elenco.
        self.calendar.setSelectedDate(day)
        menu = RoundMenu(parent=self)
        if self._copied_event is not None:
            menu.addAction(Action(FIF.PASTE, tr("calendar.menu.paste_event"), triggered=lambda: self._paste_event(day)))
            if self._copied_event["recurrence_unit"] != RECURRENCE_NONE:  # altrimenti sarebbe identica
                menu.addAction(
                    Action(FIF.PASTE, tr("calendar.menu.paste_series"), triggered=lambda: self._paste_series(day))
                )
            menu.addAction(Action(FIF.EDIT, tr("calendar.menu.paste_edit"), triggered=lambda: self._paste_and_edit(day)))
            menu.addSeparator()
        menu.addAction(Action(FIF.ADD, tr("calendar.menu.new_here"), triggered=lambda: self._on_add()))
        menu.exec(global_pos)

    def _paste_event(self, day: QDate) -> None:
        """Incolla subito: stessi titolo, nota e colore, una sola occorrenza (senza ripetizione)."""
        source = self._copied_event
        if source is None:
            return
        add_event(
            self.get_conn(),
            start_date=day.toString("yyyy-MM-dd"),
            title=source["title"],
            color=source["color"],
            note=source["note"],
        )
        self.refresh()
        self._toast(tr("calendar.event_pasted", date=day.toString(DISPLAY_DATE_QT_FORMAT)))

    def _paste_series(self, day: QDate) -> None:
        """Incolla subito l'evento con la sua ricorrenza, a partire dal giorno scelto."""
        source = self._copied_event
        if source is None:
            return
        add_event(self.get_conn(), **series_copy_at(source, date(day.year(), day.month(), day.day())))
        self.refresh()
        self._toast(tr("calendar.series_pasted", date=day.toString(DISPLAY_DATE_QT_FORMAT)))

    def _paste_and_edit(self, day: QDate) -> None:
        """Form già compilato (ricorrenza compresa) sul giorno scelto, per ritoccare prima di salvare."""
        if self._copied_event is None:
            return
        dialog = CalendarEventDialog(self.window(), start_date=day, duplicate_of=self._copied_event)
        if dialog.exec():
            add_event(self.get_conn(), **dialog.values())
            self.refresh()

    # -- azioni -----------------------------------------------------------
    def _on_duplicate(self, row) -> None:
        """Nuovo evento con i dati di quello scelto, sul giorno selezionato: di solito si
        cambia solo la data."""
        dialog = CalendarEventDialog(self.window(), start_date=self.calendar.selectedDate(), duplicate_of=row)
        if dialog.exec():
            add_event(self.get_conn(), **dialog.values())
            self.refresh()

    def add_event_today(self) -> None:
        """Da fuori (dashboard): nuovo evento con la data di oggi preselezionata."""
        self._go_to_today()
        self._on_add()

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
