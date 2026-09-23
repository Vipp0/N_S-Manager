from datetime import date, timedelta

from PySide6.QtCore import QDate, QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPen
from PySide6.QtWidgets import QCalendarWidget

from gilda_app.i18n import tr

TODAY_BORDER_COLOR = QColor("#ffb900")
TODAY_FILL_COLOR = QColor(255, 185, 0, 40)
CURRENT_WEEK_BORDER_COLOR = QColor("#2d7dfa")
SELECTED_BORDER_COLOR = QColor("#202020")
DAY_NUMBER_COLOR = QColor("#202020")
EVENT_TITLE_COLOR = QColor("#202020")
OVERFLOW_LABEL_COLOR = QColor("#5a5a5a")

NUMBER_ROW_HEIGHT = 20
DOT_DIAMETER = 9
DOT_MARGIN = 3
NUMBER_FONT_SIZE = 10
EVENT_FONT_SIZE = 10


class EventCalendarWidget(QCalendarWidget):
    """QCalendarWidget che in ogni cella mostra il numero del giorno e, sotto, un elenco
    di pallini colorati + titolo per gli eventi di quel giorno (quanti ne stanno
    nell'altezza reale della cella; il resto diventa una riga "+N altri"). Il ridisegno
    passa da paintCell, che Qt permette di sovrascrivere.

    Sovrappone anche, su ogni cella: un rettangolo sottile attorno alla riga della
    settimana corrente e un bordo/riempimento per il giorno di oggi. "Oggi"/la settimana
    corrente sono calcolati una sola volta alla creazione: un'apertura del programma a
    cavallo di mezzanotte non li aggiorna, caso limite accettabile per un programma che
    si riapre spesso."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._day_events: dict[date, list[tuple[str, str]]] = {}
        self._today = date.today()
        # setFirstDayOfWeek(Qt.Monday) è impostato da CalendarPage: qui si assume lo
        # stesso lunedì-domenica invece di reinterpretare Qt.DayOfWeek.
        self._week_start = self._today - timedelta(days=self._today.weekday())
        self._week_end = self._week_start + timedelta(days=6)

    def set_day_events(self, day_events: dict[date, list[tuple[str, str]]]) -> None:
        """day_events: per ogni giorno, (titolo, colore esadecimale) di ogni evento, in ordine."""
        self._day_events = day_events
        self.updateCells()

    def paintCell(self, painter, rect: QRect, qdate: QDate) -> None:
        py_date = date(qdate.year(), qdate.month(), qdate.day())
        events = self._day_events.get(py_date, [])
        in_month = qdate.month() == self.monthShown()

        painter.save()
        painter.setOpacity(1.0 if in_month else 0.45)

        if py_date == self._today:
            painter.fillRect(rect, TODAY_FILL_COLOR)

        number_font = QFont(painter.font())
        number_font.setPointSize(NUMBER_FONT_SIZE)
        painter.setFont(number_font)
        painter.setPen(DAY_NUMBER_COLOR)
        number_rect = QRect(rect.left(), rect.top(), rect.width() - 4, NUMBER_ROW_HEIGHT)
        painter.drawText(number_rect, Qt.AlignRight | Qt.AlignTop, str(qdate.day()))

        if events:
            event_font = QFont(painter.font())
            event_font.setPointSize(EVENT_FONT_SIZE)
            painter.setFont(event_font)
            metrics = QFontMetrics(event_font)
            row_height = metrics.height() + 3

            top = rect.top() + NUMBER_ROW_HEIGHT
            available_height = rect.bottom() - top
            max_rows = max(0, available_height // row_height) if row_height > 0 else 0

            shown = events[:max_rows]
            overflow = len(events) - len(shown)
            if overflow > 0 and max_rows > 0:
                shown = events[: max_rows - 1]
                overflow = len(events) - len(shown)

            y = top
            for title, hex_color in shown:
                dot_rect = QRect(
                    rect.left() + DOT_MARGIN,
                    y + (row_height - DOT_DIAMETER) // 2,
                    DOT_DIAMETER,
                    DOT_DIAMETER,
                )
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(hex_color))
                painter.drawEllipse(dot_rect)

                text_rect = QRect(
                    dot_rect.right() + 4,
                    y,
                    rect.right() - dot_rect.right() - 4 - DOT_MARGIN,
                    row_height,
                )
                painter.setPen(EVENT_TITLE_COLOR)
                elided = metrics.elidedText(title, Qt.ElideRight, max(0, text_rect.width()))
                painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)
                y += row_height

            if overflow > 0:
                text_rect = QRect(rect.left() + DOT_MARGIN, y, rect.width() - 2 * DOT_MARGIN, row_height)
                painter.setPen(OVERFLOW_LABEL_COLOR)
                painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, tr("calendar.more_events", n=overflow))

        painter.setOpacity(1.0)

        # Da qui in poi le evidenziazioni si applicano sempre, con o senza eventi.
        if self._week_start <= py_date <= self._week_end:
            painter.setPen(QPen(CURRENT_WEEK_BORDER_COLOR, 2))
            painter.setBrush(Qt.NoBrush)
            top = rect.top() + 1
            bottom = rect.bottom() - 1
            left = rect.left() + 1
            right = rect.right() - 1
            painter.drawLine(left, top, right, top)
            painter.drawLine(left, bottom, right, bottom)
            if py_date == self._week_start:
                painter.drawLine(left, top, left, bottom)
            if py_date == self._week_end:
                painter.drawLine(right, top, right, bottom)

        if py_date == self._today:
            painter.setPen(QPen(TODAY_BORDER_COLOR, 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect.adjusted(2, 2, -2, -2))

        if qdate == self.selectedDate():
            painter.setPen(QPen(SELECTED_BORDER_COLOR, 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect.adjusted(1, 1, -2, -2))

        painter.restore()
