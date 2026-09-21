from datetime import date

from PySide6.QtCore import QDate, QRect, Qt
from PySide6.QtGui import QColor, QFont, QPen
from PySide6.QtWidgets import QCalendarWidget

# Oltre questo numero di eventi si disegnano solo le prime fasce e un "+N".
MAX_BANDS = 4


class EventCalendarWidget(QCalendarWidget):
    """QCalendarWidget che colora ogni giorno con eventi a fasce verticali, una per evento
    (mezzo blu e mezzo rosso con due eventi). I giorni senza eventi restano quelli
    di Qt. Il ridisegno passa da paintCell, che Qt permette di sovrascrivere."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._day_colors: dict[date, list[str]] = {}

    def set_day_colors(self, day_colors: dict[date, list[str]]) -> None:
        """day_colors: per ogni giorno, i colori degli eventi in ordine."""
        self._day_colors = day_colors
        self.updateCells()

    def paintCell(self, painter, rect: QRect, qdate: QDate) -> None:
        colors = self._day_colors.get(date(qdate.year(), qdate.month(), qdate.day()))
        if not colors:
            super().paintCell(painter, rect, qdate)
            return

        painter.save()
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
        # Oggi: bordo colore d'accento; giorno selezionato: bordo più spesso.
        if qdate == QDate.currentDate():
            painter.setPen(QPen(QColor("#ffb900"), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect.adjusted(1, 1, -1, -1))
        if qdate == self.selectedDate():
            painter.setPen(QPen(QColor("#202020"), 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect.adjusted(1, 1, -2, -2))
        painter.restore()
