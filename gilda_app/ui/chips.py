"""Etichette colorate ("pillole") per stati e movimenti: Entrato, Rientrato, Uscito, Bannato, Ex membro...

Verde per chi entra o torna tra i membri attuali, rosso per chi esce o viene bannato, ambra per l'ex membro
nelle ricerche, grigio per tutto il resto: gli stessi colori del Registro eventi. Per le tabelle c'è un delegato
che disegna la pillola al posto del testo della cella (basta dare alla cella il tono con CHIP_TONE_ROLE); per i
riquadri della dashboard una ChipLabel."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QLabel, QStyledItemDelegate, QStyleOptionViewItem
from qfluentwidgets import TableItemDelegate, isDarkTheme

TONE_GOOD = "good"
TONE_BAD = "bad"
TONE_WARN = "warn"
TONE_NEUTRAL = "neutral"
TONE_OUTLINE = "outline"  # solo un contorno sottile: per un'informazione, non per un movimento

CHIP_TONE_ROLE = Qt.UserRole + 101

_LIGHT = {TONE_GOOD: "#15803d", TONE_BAD: "#c42b1c", TONE_WARN: "#b45309", TONE_NEUTRAL: "#5d5d68", TONE_OUTLINE: "#5d5d68"}
_DARK = {TONE_GOOD: "#4ade80", TONE_BAD: "#f87171", TONE_WARN: "#fbbf24", TONE_NEUTRAL: "#b4b2c2", TONE_OUTLINE: "#b4b2c2"}
PAD_X = 9
PAD_Y = 2


def chip_foreground(tone: str) -> QColor:
    return QColor((_DARK if isDarkTheme() else _LIGHT).get(tone, _LIGHT[TONE_NEUTRAL]))


def chip_background(tone: str) -> QColor:
    """Lo stesso colore del testo ma molto tenue; nessun fondo per il solo contorno."""
    color = chip_foreground(tone)
    color.setAlpha(0 if tone == TONE_OUTLINE else (34 if tone != TONE_NEUTRAL else 30))
    return color


def _rgba(color: QColor) -> str:
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"


class ChipLabel(QLabel):
    """La pillola nei riquadri della dashboard."""

    def __init__(self, text: str, tone: str, parent=None):
        super().__init__(text, parent)
        foreground = chip_foreground(tone)
        border = f"1px solid rgba({foreground.red()}, {foreground.green()}, {foreground.blue()}, 90)" if tone == TONE_OUTLINE else "none"
        self.setStyleSheet(
            f"QLabel {{ background: {_rgba(chip_background(tone))}; color: {foreground.name()}; "
            f"border: {border}; border-radius: 9px; padding: 1px {PAD_X}px; font-size: 12px; font-weight: 600; }}"
        )
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(20)


def _chip_font(base: QFont) -> QFont:
    font = QFont(base)
    font.setBold(True)
    font.setPointSizeF(max(8.0, base.pointSizeF() - 2) if base.pointSizeF() > 0 else 10.0)
    return font


def _paint_chip(painter: QPainter, option: QStyleOptionViewItem, index) -> None:
    tone = index.data(CHIP_TONE_ROLE)
    text = index.data(Qt.DisplayRole) or ""
    font = _chip_font(option.font)
    metrics = QFontMetrics(font)
    height = metrics.height() + 2 * PAD_Y + 2
    left = option.rect.left() + 10
    width = min(metrics.horizontalAdvance(text) + 2 * PAD_X, max(20, option.rect.right() - left - 6))
    rect = QRectF(left, option.rect.center().y() - height / 2 + 0.5, width, height)
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(chip_background(tone))
    if tone == TONE_OUTLINE:
        outline = chip_foreground(tone)
        outline.setAlpha(90)
        painter.setPen(QPen(outline, 1))
    else:
        painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(rect, height / 2, height / 2)
    painter.setPen(chip_foreground(tone))
    painter.setFont(font)
    painter.drawText(rect, Qt.AlignCenter, metrics.elidedText(text, Qt.ElideRight, int(width - 2 * PAD_X)))
    painter.restore()


class ChipDelegate(QStyledItemDelegate):
    """Per le tabelle semplici (QTableWidget): le celle con un tono mostrano la pillola, le altre il testo."""

    def initStyleOption(self, option, index) -> None:
        super().initStyleOption(option, index)
        if index.data(CHIP_TONE_ROLE):
            option.text = ""

    def paint(self, painter, option, index) -> None:
        super().paint(painter, option, index)
        if index.data(CHIP_TONE_ROLE):
            _paint_chip(painter, option, index)


class FluentChipDelegate(TableItemDelegate):
    """Lo stesso per le tabelle qfluentwidgets (TableWidget), che hanno un delegato proprio."""

    def initStyleOption(self, option, index) -> None:
        super().initStyleOption(option, index)
        if index.data(CHIP_TONE_ROLE):
            option.text = ""

    def paint(self, painter, option, index) -> None:
        super().paint(painter, option, index)
        if index.data(CHIP_TONE_ROLE):
            _paint_chip(painter, option, index)
