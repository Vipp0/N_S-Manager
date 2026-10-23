"""Schermata di caricamento stagionale (Qt), mostrata nei periodi di festa al posto di quella normale.

La schermata normale la disegna l'exe prima ancora che parta Python ed è un'immagine fissa, incorporata
quando si costruisce l'exe: non può cambiare con la data. Questa invece parte appena Qt è pronto, prima
di caricare il resto del programma, e prende il posto dell'altra con una breve dissolvenza. Importa solo
Qt, non il resto dell'interfaccia, proprio per comparire il prima possibile.

È un semplice widget senza cornice e non un QSplashScreen: la prima comparsa di un QSplashScreen costa
circa un secondo in più, e qui ogni istante di attesa si vede."""
import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from gilda_app.seasons import Season

FADE_SECONDS = 0.3


class SeasonalSplash(QWidget):
    def __init__(self, season: Season, base_text: str):
        super().__init__(None, Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self._pixmap = QPixmap(str(season.splash_path))
        self._base_text = base_text
        self._color = QColor(season.loading_color)
        self._message = ""
        self.setFont(QFont("Segoe UI", 14))
        self.setFixedSize(self._pixmap.size())
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            self.move(screen.geometry().center() - self.rect().center())
        self.set_dots(3)

    def pixmap(self) -> QPixmap:
        return self._pixmap

    def set_dots(self, count: int) -> None:
        """"Loading." / ".." / "..." come nella schermata normale. A capo finale: alza il testo dal bordo."""
        self._message = self._base_text + "." * count + "\n"
        self.repaint()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._pixmap)
        painter.setPen(self._color)
        painter.drawText(self.rect(), int(Qt.AlignHCenter | Qt.AlignBottom), self._message)

    def fade_in(self, seconds: float = FADE_SECONDS) -> None:
        """Compare gradualmente sopra la schermata dell'exe (dissolvenza incrociata)."""
        self.setWindowOpacity(0.0)
        self.show()
        start = time.perf_counter()
        while True:
            progress = (time.perf_counter() - start) / seconds
            self.setWindowOpacity(min(1.0, progress))
            QApplication.processEvents()
            if progress >= 1.0:
                break
            time.sleep(0.01)

    def finish(self, window: QWidget) -> None:
        """Si chiude quando la finestra principale è comparsa davvero (come QSplashScreen.finish)."""
        handle = window.windowHandle()
        deadline = time.perf_counter() + 2.0
        while handle is not None and not handle.isExposed() and time.perf_counter() < deadline:
            QApplication.processEvents()
        self.close()
