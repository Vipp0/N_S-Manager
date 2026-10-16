from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from gilda_app.i18n import tr
from gilda_app.utils.server_status import RegionStatus, remaining_text

COLOR_ONLINE = "#1a7f37"
COLOR_MAINTENANCE = "#c42b1c"
COLOR_ANNOUNCED = "#d9730d"  # arancione: manutenzione ordinaria annunciata
COLOR_UNKNOWN = "#8a8886"


def describe_region(status: RegionStatus | None) -> tuple[str, str]:
    """(testo, colore) con cui mostrare lo stato di una regione."""
    if status is None:
        return tr("server.unknown"), COLOR_UNKNOWN
    if not status.in_maintenance:
        return tr("server.online"), COLOR_ONLINE
    remaining = remaining_text(status)
    base = "server.maintenance"
    if status.estimated:
        base = "server.maintenance_official" if status.official else "server.maintenance_estimated"
    if remaining:
        return tr(f"{base}_remaining" if status.estimated else "server.maintenance_remaining", time=remaining), COLOR_MAINTENANCE
    return tr(base), COLOR_MAINTENANCE


def describe_region_parts(status: RegionStatus | None) -> tuple[str, str | None, str]:
    """Come describe_region, ma in due pezzi: (titolo breve, dettaglio o None, colore). Il riquadro
    BDO della dashboard mostra il titolo in carattere grande: con il testo intero ("In manutenzione,
    secondo l'avviso (fine tra 1h 29m)") il riquadro si allargava più degli altri."""
    if status is None:
        return tr("server.unknown"), None, COLOR_UNKNOWN
    if not status.in_maintenance:
        return tr("server.online"), None, COLOR_ONLINE
    details = []
    if status.estimated:
        details.append(tr("server.detail.official" if status.official else "server.detail.estimated"))
    remaining = remaining_text(status)
    if remaining:
        details.append(tr("server.detail.remaining", time=remaining))
    return tr("server.headline.maintenance"), " · ".join(details) or None, COLOR_MAINTENANCE


def announced_color(temporary: bool) -> str:
    """Colore di una manutenzione annunciata ma non ancora iniziata: arancione se ordinaria, rosso
    se temporanea/straordinaria (fuori programma). Quando è in corso è sempre rosso. Unico punto da
    cui prendono il colore dashboard, banner e scheda BDO, così non possono divergere."""
    return COLOR_MAINTENANCE if temporary else COLOR_ANNOUNCED


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
