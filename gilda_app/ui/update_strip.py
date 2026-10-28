from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QToolButton, QWidget
from qfluentwidgets import BodyLabel, StrongBodyLabel, Theme, qconfig, themeColor
from qfluentwidgets import FluentIcon as FIF

from gilda_app.i18n import tr


class UpdateStrip(QWidget):
    """Striscia a tutta larghezza sopra le pagine, nel colore d'accento, per avvisare che c'è una
    nuova versione quando il programma è già aperto. Sta nel layout (non sopra i contenuti): si vede
    da ogni scheda, non copre niente e resta finché non la si chiude. `clicked`: pulsante "Vedi"."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(46)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 12, 0)
        layout.setSpacing(12)
        icon = QLabel(self)
        icon.setPixmap(FIF.UPDATE.icon(Theme.DARK).pixmap(20, 20))
        layout.addWidget(icon)
        self._title = StrongBodyLabel(self)
        self._text = BodyLabel(self)
        layout.addWidget(self._title)
        layout.addWidget(self._text)
        layout.addStretch(1)
        self._button = QPushButton(tr("update.available.notice_button"), self)
        self._button.setCursor(Qt.PointingHandCursor)
        self._button.setFont(self._text.font())
        self._button.clicked.connect(self.clicked)
        layout.addWidget(self._button)
        self._close = QToolButton(self)
        self._close.setIcon(FIF.CLOSE.icon(Theme.DARK))
        self._close.setCursor(Qt.PointingHandCursor)
        self._close.setStyleSheet(
            "QToolButton { background: transparent; border: none; border-radius: 4px; padding: 6px; }"
            "QToolButton:hover { background: rgba(255, 255, 255, 50); }"
        )
        self._close.clicked.connect(self.hide)
        layout.addWidget(self._close)
        self._title.setStyleSheet("color: white;")
        self._text.setStyleSheet("color: white;")
        qconfig.themeColorChanged.connect(self._apply_colors)
        self._apply_colors()
        self.hide()

    def _apply_colors(self, *_args) -> None:
        # Il colore d'accento cambia con i temi stagionali: il pulsante bianco ne prende il testo.
        accent = themeColor().name()
        self._button.setStyleSheet(
            f"QPushButton {{ background: white; color: {accent}; border: none; border-radius: 5px; "
            "padding: 5px 18px; font-weight: 600; }"
            "QPushButton:hover { background: rgba(255, 255, 255, 230); }"
            "QPushButton:pressed { background: rgba(255, 255, 255, 200); }"
        )
        self.update()

    def show_version(self, version: str) -> None:
        self._title.setText(tr("update.available.title"))
        self._text.setText(tr("update.available.notice", version=version))
        self.show()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(themeColor()))
