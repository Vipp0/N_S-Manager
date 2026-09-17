"""Icona "divieto" per la scheda Bannati: il set di FluentIcon disponibile non
include un simbolo di divieto (cerchio con barra diagonale), lo disegniamo."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPen, QPixmap

_ban_icon: QIcon | None = None


def ban_icon() -> QIcon:
    global _ban_icon
    if _ban_icon is None:
        size = 64
        margin = 6
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.black)
        pen.setWidth(6)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        painter.drawEllipse(QRectF(margin, margin, size - 2 * margin, size - 2 * margin))
        inset = margin + 11
        painter.drawLine(inset, size - inset, size - inset, inset)
        painter.end()

        _ban_icon = QIcon(pixmap)
    return _ban_icon
