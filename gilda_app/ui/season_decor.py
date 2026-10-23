"""Decorazioni dei temi stagionali: immagini negli angoli e nei vuoti, mai sopra tabelle o pulsanti.

Un tema le prevede se in resources/ ci sono i file deco_<tema>_<nome>.png; quelli che mancano si saltano. Si
disegnano sopra la pagina senza intercettare il mouse, si adattano alla larghezza della finestra e spariscono
con il tema."""
from dataclasses import dataclass

from PySide6.QtCore import QEvent, QRect, Qt
from PySide6.QtGui import QPainter, QPixmap, QTransform
from PySide6.QtWidgets import QWidget

from gilda_app.seasons import Season


@dataclass(frozen=True)
class DecorItem:
    name: str  # parte del nome del file: deco_<tema>_<name>.png
    height: int  # altezza a schermo in pixel (la larghezza segue le proporzioni)
    right: int = 0  # distanza dal bordo destro della pagina
    left: int | None = None  # se indicata, distanza dal bordo sinistro al posto di quella dal destro
    top: int = 0  # distanza dal bordo alto della pagina
    mirror: bool = False  # specchiata in orizzontale (la ragnatela d'angolo è disegnata per l'angolo in alto a sinistra)
    min_page_width: int = 0  # sotto questa larghezza della pagina non si disegna: lascia spazio al contenuto
    opacity: float = 1.0


class OrnamentedPage:
    """Per le pagine con un solo ornamento di tema in self._decor: aggiunge set_decor(season), che il
    programma chiama a ogni cambio di tema. Va messa prima di QWidget tra le classi base."""

    _decor: "DecorOverlay"

    def set_decor(self, season: Season | None) -> None:
        self._decor.set_season(season)


class DecorOverlay(QWidget):
    """Strato trasparente sopra una pagina che disegna le decorazioni del tema in corso."""

    def __init__(self, page: QWidget, items: list[DecorItem]):
        super().__init__(page)
        self._page = page
        self._items = items
        self._pixmaps: dict[str, QPixmap] = {}
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        page.installEventFilter(self)
        self.hide()

    def set_season(self, season: Season | None) -> None:
        self._pixmaps = {}
        if season is not None:
            for item in self._items:
                path = season.decor_path(item.name)
                if path.exists():
                    pixmap = QPixmap(str(path))
                    if item.mirror:
                        pixmap = pixmap.transformed(QTransform().scale(-1, 1))
                    self._pixmaps[item.name] = pixmap
        self.setVisible(bool(self._pixmaps))
        self._follow_page()
        self.update()

    def eventFilter(self, obj, event) -> bool:
        if obj is self._page and event.type() == QEvent.Resize:
            self._follow_page()
        return False

    def _follow_page(self) -> None:
        self.setGeometry(self._page.rect())
        self.raise_()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        for item in self._items:
            pixmap = self._pixmaps.get(item.name)
            if pixmap is None or self.width() < item.min_page_width:
                continue
            width = round(item.height * pixmap.width() / pixmap.height())
            painter.setOpacity(item.opacity)
            x = item.left if item.left is not None else self.width() - item.right - width
            painter.drawPixmap(QRect(x, item.top, width, item.height), pixmap)
