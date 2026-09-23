from datetime import date, timedelta

from PySide6.QtCore import QDate, QRect, Qt
from PySide6.QtGui import QColor, QFont, QPen
from PySide6.QtWidgets import QCalendarWidget

# Oltre questo numero di eventi si disegnano solo le prime fasce e un "+N".
MAX_BANDS = 4

TODAY_BORDER_COLOR = QColor("#ffb900")
TODAY_FILL_COLOR = QColor(255, 185, 0, 40)
CURRENT_WEEK_BORDER_COLOR = QColor("#2d7dfa")
SELECTED_BORDER_COLOR = QColor("#202020")


class EventCalendarWidget(QCalendarWidget):
    """QCalendarWidget che colora ogni giorno con eventi a fasce verticali, una per evento
    (mezzo blu e mezzo rosso con due eventi). I giorni senza eventi restano quelli
    di Qt. Il ridisegno passa da paintCell, che Qt permette di sovrascrivere.

    Sovrappone anche, su ogni cella indipendentemente dal fatto che abbia eventi: un
    rettangolo sottile attorno alla riga della settimana corrente e un bordo/riempimento
    per il giorno di oggi. "Oggi"/la settimana corrente sono calcolati una sola volta alla
    creazione: un'apertura del programma a cavallo di mezzanotte non li aggiorna, caso
    limite accettabile per un programma che si riapre spesso."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._day_colors: dict[date, list[str]] = {}
        self._today = date.today()
        # setFirstDayOfWeek(Qt.Monday) è impostato da CalendarPage: qui si assume lo
        # stesso lunedì-domenica invece di reinterpretare Qt.DayOfWeek.
        self._week_start = self._today - timedelta(days=self._today.weekday())
        self._week_end = self._week_start + timedelta(days=6)

    def set_day_colors(self, day_colors: dict[date, list[str]]) -> None:
        """day_colors: per ogni giorno, i colori degli eventi in ordine."""
        self._day_colors = day_colors
        self.updateCells()

    def paintCell(self, painter, rect: QRect, qdate: QDate) -> None:
        py_date = date(qdate.year(), qdate.month(), qdate.day())
        colors = self._day_colors.get(py_date)

        painter.save()

        if colors:
            in_month = qdate.month() == self.monthShown()
            painter.setOpacity(1.0 if in_month else 0.45)

            shown = colors[:MAX_BANDS]
            band_width = rect.width() / len(shown)
            for index, hex_color in enumerate(shown):
                left = rect.left() + round(index * band_width)
                right = rect.left() + round((index + 1) * band_width)
                painter.fillRect(QRect(left, rect.top(), right - left, rect.height()), QColor(hex_color))

            # Numero del giorno: bianco con contorno scuro, leggibile su qualsiasi fascia.
            font = QFont(painter.font())
            font.setBold(True)
            painter.setFont(font)
            text = str(qdate.day())
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
                painter.setPen(QColor(0, 0, 0, 200))
                painter.drawText(rect.translated(dx, dy), Qt.AlignCenter, text)
            painter.setPen(QColor("#ffffff"))
            painter.drawText(rect, Qt.AlignCenter, text)

            extra = len(colors) - MAX_BANDS
            if extra > 0:
                small = QFont(font)
                small.setPointSize(max(6, font.pointSize() - 2))
                painter.setFont(small)
                badge = f"+{extra}"
                corner = rect.adjusted(0, 0, -3, -2)
                painter.setPen(QColor(0, 0, 0, 220))
                painter.drawText(corner.translated(1, 1), Qt.AlignRight | Qt.AlignBottom, badge)
                painter.setPen(QColor("#ffffff"))
                painter.drawText(corner, Qt.AlignRight | Qt.AlignBottom, badge)

            painter.setOpacity(1.0)
        else:
            # Riempimento leggero per oggi quando non ci sono fasce evento a coprire lo
            # sfondo: disegnato prima del numero, così il testo resta sopra.
            if py_date == self._today:
                painter.fillRect(rect, TODAY_FILL_COLOR)
            super().paintCell(painter, rect, qdate)

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
