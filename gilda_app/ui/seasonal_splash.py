"""Schermata di caricamento stagionale (Qt), mostrata nei periodi di festa al posto di quella normale.

La schermata normale la disegna l'exe prima ancora che parta Python ed è un'immagine fissa, incorporata
quando si costruisce l'exe: non può cambiare con la data. Questa invece parte appena Qt è pronto, prima
di caricare il resto del programma, e prende il posto dell'altra (che si chiude). Importa solo Qt, non il
resto dell'interfaccia, proprio per comparire il prima possibile."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import QSplashScreen

from gilda_app.seasons import Season


class SeasonalSplash(QSplashScreen):
    def __init__(self, season: Season, base_text: str):
        super().__init__(QPixmap(str(season.splash_path)))
        self._base_text = base_text
        self._color = QColor(season.loading_color)
        self.setFont(QFont("Segoe UI", 14))
        self.set_dots(3)

    def set_dots(self, count: int) -> None:
        """"Loading." / ".." / "..." come nella schermata normale. A capo finale: alza il testo dal bordo."""
        self.showMessage(self._base_text + "." * count + "\n", Qt.AlignHCenter | Qt.AlignBottom, self._color)
