from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QWidget

from gilda_app.i18n import tr
from gilda_app.utils.event_colors import DEFAULT_EVENT_COLOR, EVENT_COLORS, nearest_preset

SWATCH_SIZE = 28


class ColorSwatchPicker(QWidget):
    """Fila di pallini colorati cliccabili (uno solo selezionato) per scegliere tra i
    colori prefissati degli eventi."""

    colorChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}

        for name_key, hex_color in EVENT_COLORS:
            button = QPushButton(self)
            button.setCheckable(True)
            button.setFixedSize(SWATCH_SIZE, SWATCH_SIZE)
            button.setCursor(Qt.PointingHandCursor)
            button.setToolTip(tr(name_key))
            radius = SWATCH_SIZE // 2
            # Il pallino selezionato ha un anello scuro; gli altri solo un bordo sottile.
            button.setStyleSheet(
                f"QPushButton {{ background-color: {hex_color}; border: 2px solid transparent;"
                f" border-radius: {radius}px; }}"
                f"QPushButton:hover {{ border: 2px solid #9a9a9a; }}"
                f"QPushButton:checked {{ border: 3px solid #202020; }}"
            )
            button.clicked.connect(lambda _=False, c=hex_color: self.colorChanged.emit(c))
            self._group.addButton(button)
            layout.addWidget(button)
            self._buttons[hex_color] = button

        layout.addStretch(1)
        self.setColor(DEFAULT_EVENT_COLOR)

    def color(self) -> str:
        for hex_color, button in self._buttons.items():
            if button.isChecked():
                return hex_color
        return DEFAULT_EVENT_COLOR

    def setColor(self, hex_color: str) -> None:
        """Seleziona un colore; se non è tra i prefissati (evento vecchio) sceglie il più vicino."""
        key = hex_color if hex_color in self._buttons else nearest_preset(hex_color)
        self._buttons[key].setChecked(True)
