from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from gilda_app.i18n import tr
from gilda_app.utils.server_status import RegionStatus, remaining_text

COLOR_ONLINE = "#1a7f37"
COLOR_MAINTENANCE = "#c42b1c"
COLOR_UNKNOWN = "#8a8886"


def describe_region(status: RegionStatus | None) -> tuple[str, str]:
    """(testo, colore) con cui mostrare lo stato di una regione."""
    if status is None:
        return tr("server.unknown"), COLOR_UNKNOWN
    if not status.in_maintenance:
        return tr("server.online"), COLOR_ONLINE
    remaining = remaining_text(status)
    if remaining:
        return tr("server.maintenance_remaining", time=remaining), COLOR_MAINTENANCE
    return tr("server.maintenance"), COLOR_MAINTENANCE


def describe_error(kind: str) -> tuple[str, str]:
    return tr(f"server.error.{kind}"), COLOR_UNKNOWN


class ServerStatusFooter(QWidget):
    """Striscia in fondo alla finestra, a destra: "Stato server  EU · Online" colorato.
    Un click ovunque sulla striscia apre la scheda BDO con il dettaglio."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(28)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.addStretch(1)
        self._title = QLabel(tr("footer.server_status"), self)
        self._title.setStyleSheet("color: #8a8886;")
        self._value = QLabel(self)
        layout.addWidget(self._title)
        layout.addWidget(self._value)
        self.set_state("", tr("server.unknown"), COLOR_UNKNOWN)

    def set_state(self, region_label: str, text: str, color: str) -> None:
        prefix = f"{region_label} · " if region_label else ""
        self._value.setText(f"<b>{prefix}{text}</b>")
        self._value.setStyleSheet(f"color: {color};")

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
