from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import CardWidget, CaptionLabel, FluentIcon as FIF, PushButton, StrongBodyLabel, SubtitleLabel

from gilda_app.i18n import tr
from gilda_app.ui.server_status_footer import COLOR_UNKNOWN, describe_error, describe_region
from gilda_app.utils.server_status import REGIONS, RegionStatus


class BdoPage(QWidget):
    """Scheda con i dati presi dall'API di bdoalerts.net. Costruita a blocchi (una card
    per funzione): oggi solo lo stato dei server, le prossime funzioni si aggiungono
    come nuove card sotto senza toccare le altre."""

    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        layout.addWidget(SubtitleLabel(tr("bdo.title"), self))

        status_card = CardWidget(self)
        card_layout = QVBoxLayout(status_card)
        card_layout.addWidget(StrongBodyLabel(tr("bdo.server_status"), status_card))
        self._grid = QGridLayout()
        self._grid.setHorizontalSpacing(24)
        self._value_labels: dict[str, QLabel] = {}
        for row, region in enumerate(REGIONS):
            self._grid.addWidget(QLabel(tr(f"region.{region}"), status_card), row, 0)
            value = QLabel(status_card)
            self._grid.addWidget(value, row, 1)
            self._value_labels[region] = value
        self._grid.setColumnStretch(2, 1)
        card_layout.addLayout(self._grid)

        self._message = CaptionLabel("", status_card)
        self._message.setWordWrap(True)
        card_layout.addWidget(self._message)
        refresh_btn = PushButton(FIF.SYNC, tr("bdo.refresh"), status_card)
        refresh_btn.clicked.connect(self.refresh_requested)
        card_layout.addWidget(refresh_btn, 0, Qt.AlignLeft)
        layout.addWidget(status_card)
        layout.addStretch(1)

        self.show_error("no_key")

    def _set_value(self, region: str, text: str, color: str) -> None:
        label = self._value_labels[region]
        label.setText(f"<b>{text}</b>")
        label.setStyleSheet(f"color: {color};")

    def show_status(self, statuses: dict[str, RegionStatus]) -> None:
        self._message.setText("")
        for region in REGIONS:
            text, color = describe_region(statuses.get(region))
            self._set_value(region, text, color)

    def show_error(self, kind: str) -> None:
        """Errore (o chiave mancante): le regioni tornano "n/d" e sotto compare il motivo."""
        for region in REGIONS:
            self._set_value(region, tr("server.unknown"), COLOR_UNKNOWN)
        self._message.setText(describe_error(kind)[0])
