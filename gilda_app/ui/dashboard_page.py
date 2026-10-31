import html
from datetime import date
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    FluentIcon as FIF,
    PrimaryPushButton,
    PushButton,
    ScrollArea,
    StrongBodyLabel,
    isDarkTheme,
    themeColor,
)

from gilda_app.capacity import guild_capacity
from gilda_app.db import dashboard as queries
from gilda_app.db import stats
from gilda_app.i18n import tr
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO
from gilda_app.ui.chips import TONE_BAD, TONE_GOOD, TONE_OUTLINE, ChipLabel
from gilda_app.ui.dashboard_cover import FONT_FAMILY, CoverHero
from gilda_app.ui.season_decor import DecorItem, DecorOverlay, snow
from gilda_app.utils.date_format import iso_to_display, relative_day_label
from gilda_app.version import __version__

TILE_MIN_WIDTH = 300
MAX_COLUMNS = 4
# Decorazioni del tema stagionale sopra la dashboard: negli angoli alti, dove le schede sono vuote.
DASHBOARD_DECOR = [
    DecorItem("web", height=150, mirror=True, min_page_width=700, opacity=0.95),
    DecorItem("spider", height=135, right=170, min_page_width=900, opacity=0.95),
    # Natale: altre due palline appese a fili diversi (più a sinistra, solo se c'è posto accanto al logo) e fiocchi
    # di neve tra il titolo e il logo. Mancano i file negli altri temi, e allora non si disegnano.
    DecorItem("spider2", height=95, right=255, min_page_width=1150, opacity=0.95),
    DecorItem("spider3", height=85, right=335, min_page_width=1300, opacity=0.95),  # corta: sotto c'è la legenda del grafico
    *snow(right=430),
]
CLUSTER_WIDTH = 240  # larghezza del gruppo di decorazioni nel vuoto in fondo alla griglia delle informazioni
GREETING_ICON_SIZE = 26
NOTES_PREVIEW_LINES = 5

# Chiavi dei riquadri diversi dalle tre liste membri (le liste usano il loro status).
TILE_STATS = "stats"
TILE_CALENDAR = "calendar"
TILE_BDO = "bdo"
TILE_NOTES = "notes"
TILE_SETTINGS = "settings"

WORDMARK_PATH = Path(__file__).resolve().parent.parent / "resources" / "wordmark.png"
WORDMARK_HEIGHT = 66
CHIP_ROW_HEIGHT = 21  # altezza di una riga dei riquadri (come le righe di testo)
CHIP_MIN_WIDTH = 76
COVER_WIDE_WIDTH = 1000  # da questa larghezza della pagina il grafico sta accanto ai numeri, sotto va su due file
COVER_BAND_WIDE_WIDTH = 1150  # da qui le quattro sezioni stanno su una fila sola, sotto su due
TILE_KEYS_INFO = ("info_joins", "info_anniversaries")

_VALUE_STYLE = "font-size: 28px; font-weight: 600;"
# Le righe che riguardano oggi (eventi, festività, compleanni, anniversari): grassetto e
# verde scuro, così si distinguono da quelle dei giorni successivi.
TODAY_COLOR = "#15803d"
# Come TODAY_COLOR, ma per chi non è più un membro attuale (compleanno degli ex membri).
FORMER_TODAY_COLOR = "#b45309"
# Righe dei riquadri di informazioni (movimenti, compleanni, anniversari): le stesse per tutti, così
# la fila è alta quanto serve a sei righe e nessun riquadro resta con un vuoto sotto.
INFO_ROWS = 6
# I compleanni sono sempre INFO_ROWS, anche se il più vicino è fra mesi (un anno di giorni basta a trovare
# il prossimo di chiunque).
BIRTHDAY_DAYS = 366
# Etichetta dei movimenti: verde per chi entra o rientra, rossa per chi esce o viene bannato (come nel Registro eventi).
MOVE_TONES = {
    queries.MOVE_JOINED: TONE_GOOD,
    queries.MOVE_REJOINED: TONE_GOOD,
    queries.MOVE_LEFT: TONE_BAD,
    queries.MOVE_BANNED: TONE_BAD,
}
# Lo stesso per gli anniversari: si cercano nell'anno intero, così il riquadro è pieno quanto gli altri.
ANNIVERSARY_DAYS = 366


def day_text(day: date, today: date, fallback: str) -> str:
    """"Oggi" / "Domani" / "Ieri" per i giorni vicini, altrimenti la data (fallback)."""
    key = relative_day_label(day, today)
    return tr(key) if key else fallback


class MaintenanceBanner(CardWidget):
    """Striscia rossa in cima alla dashboard, visibile solo quando c'è una manutenzione
    annunciata non ancora iniziata (vedi MainWindow._update_maintenance_banner): niente
    annuncio, niente striscia, nessuno spazio occupato. Click -> scheda BDO."""

    _COLOR = QColor("#c42b1c")  # stesso rosso di "in manutenzione" nel footer/scheda BDO
    # Colore attuale: serve già durante la costruzione (la scheda di Qt chiede lo sfondo subito),
    # poi lo cambia set_text().
    _color = QColor("#c42b1c")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        self._color = QColor(self._COLOR)
        self._label = StrongBodyLabel(self)
        self._label.setStyleSheet(f"color: {self._color.name()};")
        layout.addWidget(self._label)
        layout.addStretch(1)
        self.hide()

    def _tinted(self, alpha: int) -> QColor:
        return QColor(self._color.red(), self._color.green(), self._color.blue(), alpha)

    def _normalBackgroundColor(self):
        return self._tinted(30 if isDarkTheme() else 26)

    def _hoverBackgroundColor(self):
        return self._tinted(45 if isDarkTheme() else 40)

    def _pressedBackgroundColor(self):
        return self._tinted(55)

    def set_text(self, text: str | None, color: str | None = None) -> None:
        """color: colore esadecimale del testo e dello sfondo tenue (di default il rosso)."""
        self.setVisible(bool(text))
        if text:
            self._color = QColor(color or self._COLOR)
            self._label.setStyleSheet(f"color: {self._color.name()};")
            self._label.setText(text)
            # Qt tiene in memoria il colore di sfondo: cambiato il colore, va riapplicato a mano.
            self.setBackgroundColor(self._normalBackgroundColor())
            self.update()


class DashboardTile(CardWidget):
    """Riquadro cliccabile: titolo con icona, un valore grande opzionale e qualche riga."""

    def __init__(self, icon, title: str, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)
        head = QHBoxLayout()
        icon_label = QLabel(self)
        qicon = icon.icon() if hasattr(icon, "icon") else icon
        icon_label.setPixmap(qicon.pixmap(18, 18))
        head.addWidget(icon_label)
        head.addWidget(StrongBodyLabel(title, self))
        head.addStretch(1)
        layout.addLayout(head)
        self._value = QLabel(self)
        self._value.setStyleSheet(_VALUE_STYLE)
        # Mai più largo di quanto il riquadro concede: un titolo lungo va a capo invece di
        # allargare la colonna (e con lei tutti i riquadri della riga).
        self._value.setWordWrap(True)
        self._value.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout.addWidget(self._value)
        self._lines = BodyLabel(self)
        self._lines.setWordWrap(True)
        self._lines.setTextFormat(Qt.RichText)
        layout.addWidget(self._lines)
        # Righe con un'etichetta colorata in fondo (movimenti, compleanni degli ex membri): una griglia di
        # widget al posto del testo, perché una pillola arrotondata nel testo formattato non si può disegnare.
        self._chip_rows = QWidget(self)
        self._chip_grid = QGridLayout(self._chip_rows)
        self._chip_grid.setContentsMargins(0, 1, 0, 0)  # un pixel di margine: le righe partono alla stessa altezza di quelle in testo
        self._chip_grid.setHorizontalSpacing(14)
        self._chip_grid.setVerticalSpacing(0)
        self._chip_grid.setColumnStretch(1, 1)
        layout.addWidget(self._chip_rows)
        self._chip_rows.hide()
        layout.addStretch(1)
        self.setCursor(Qt.PointingHandCursor)

    # Il colore di passaggio predefinito di CardWidget è bianco quasi trasparente: su un
    # fondo chiaro non si vede. Qui il riquadro si tinge di azzurro tenue al passaggio
    # del mouse, un po' più scuro mentre lo si preme, con un sottile bordo d'accento.
    def _hoverBackgroundColor(self):
        return QColor(255, 255, 255, 30) if isDarkTheme() else QColor(0, 120, 212, 22)

    def _pressedBackgroundColor(self):
        return QColor(255, 255, 255, 18) if isDarkTheme() else QColor(0, 120, 212, 40)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.isHover:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(QColor(0, 120, 212, 110), 1.2))
            painter.setBrush(Qt.NoBrush)
            r = self.borderRadius
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), r, r)

    def set_content(
        self,
        value: str,
        lines: list,
        value_color: str | None = None,
        today_lines: frozenset[int] = frozenset(),
        today_colors: dict[int, str] | None = None,
    ) -> None:
        """lines: stringhe semplici oppure coppie (etichetta, testo): le etichette (Oggi,
        Domani, una data) stanno in una colonna allineata, così i testi partono tutti dallo
        stesso punto. Una terza voce (testo, tono) aggiunge in fondo alla riga un'etichetta colorata
        (vedi chips.py). today_lines: indici delle righe da evidenziare perché riguardano oggi;
        today_colors: colore diverso da TODAY_COLOR per alcune di quelle righe."""
        self._value.setText(value)
        self._value.setVisible(bool(value))
        self._value.setStyleSheet(_VALUE_STYLE + (f" color: {value_color};" if value_color else ""))
        def fmt(index: int, text: str) -> str:
            text = html.escape(text)
            color = (today_colors or {}).get(index, TODAY_COLOR)
            return f'<b style="color: {color};">{text}</b>' if index in today_lines else text

        with_chips = any(isinstance(line, tuple) and len(line) == 3 for line in lines)
        self._lines.setVisible(not with_chips)
        self._chip_rows.setVisible(with_chips)
        if with_chips:
            self._fill_chip_rows(lines, fmt)
            return
        if any(isinstance(line, tuple) for line in lines):
            rows = []
            for index, line in enumerate(lines):
                if isinstance(line, tuple):
                    label, text = line
                    rows.append(f"<tr><td>{fmt(index, label)}&nbsp;&nbsp;&nbsp;</td><td>{fmt(index, text)}</td></tr>")
                else:
                    rows.append(f'<tr><td colspan="2">{fmt(index, line)}</td></tr>')
            self._lines.setText('<table cellspacing="0" cellpadding="1">' + "".join(rows) + "</table>")
        else:
            self._lines.setText("<br>".join(fmt(index, line) for index, line in enumerate(lines)))


    def _fill_chip_rows(self, lines: list, fmt: Callable[[int, str], str]) -> None:
        while self._chip_grid.count():
            widget = self._chip_grid.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        for row, line in enumerate(lines):
            label, text, chip = (line + (None,))[:3] if isinstance(line, tuple) else ("", line, None)
            # Data e nome hanno lo stesso carattere, la stessa altezza di riga e partono dall'alto: stanno sulla
            # stessa linea (anche se il nome va a capo), come nei riquadri con la tabella di testo.
            if label:
                when = BodyLabel(fmt(row, label), self._chip_rows)
                when.setTextFormat(Qt.RichText)
                when.setAlignment(Qt.AlignLeft | Qt.AlignTop)
                when.setFixedHeight(CHIP_ROW_HEIGHT)
                self._chip_grid.addWidget(when, row, 0, Qt.AlignTop)
            body = BodyLabel(fmt(row, text), self._chip_rows)
            body.setTextFormat(Qt.RichText)
            body.setWordWrap(True)
            body.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            body.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)  # un nome lungo va a capo, non allarga
            body.setMinimumHeight(CHIP_ROW_HEIGHT)
            self._chip_grid.addWidget(body, row, 1 if label else 0, 1, 2 if not label else 1)
            if chip:
                badge = ChipLabel(chip[0], chip[1], self._chip_rows)
                badge.setMinimumWidth(CHIP_MIN_WIDTH)  # tutte della stessa larghezza: il bordo sinistro è dritto
                self._chip_grid.addWidget(badge, row, 2, Qt.AlignRight | Qt.AlignTop)


class InfoCard(DashboardTile):
    """Riquadro solo informativo: stesso aspetto dei riquadri ma senza effetto al
    passaggio del mouse e senza click."""

    def __init__(self, icon, title: str, parent=None):
        super().__init__(icon, title, parent)
        self.setCursor(Qt.ArrowCursor)

    def _hoverBackgroundColor(self):
        return self._normalBackgroundColor()

    def _pressedBackgroundColor(self):
        return self._normalBackgroundColor()

    def paintEvent(self, event) -> None:
        CardWidget.paintEvent(self, event)


class CoverCard(CardWidget):
    """La scheda unica della copertina: sfondo come un riquadro, ma senza effetto al passaggio del mouse (le zone
    cliccabili sono quelle dentro) e con una sfumatura nel colore d'accento sulla parte alta."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hero: QWidget | None = None

    def _hoverBackgroundColor(self):
        return self._normalBackgroundColor()

    def _pressedBackgroundColor(self):
        return self._normalBackgroundColor()

    def paintEvent(self, event) -> None:
        CardWidget.paintEvent(self, event)
        if self.hero is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(self.rect().adjusted(1, 1, -1, -1), self.borderRadius, self.borderRadius)
        painter.setClipPath(clip)
        tint = QColor(themeColor())
        tint.setAlpha(46 if isDarkTheme() else 34)
        gradient = QLinearGradient(0, 0, self.width() * 0.62, 0)
        gradient.setColorAt(0, tint)
        tint.setAlpha(0)
        gradient.setColorAt(1, tint)
        painter.fillRect(0, 0, self.width(), self.hero.height(), gradient)


class CoverSection(DashboardTile):
    """Una sezione della fascia in basso nella copertina (calendario, BDO, note, impostazioni): senza bordo e
    sfondo propri, si illumina al passaggio del mouse e ha una linea di separazione dalle vicine."""

    def __init__(self, icon, title: str, parent=None):
        super().__init__(icon, title, parent)
        self.setMinimumHeight(0)
        self.edge_left = False
        self.edge_top = False

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.isHover:
            tint = QColor(themeColor())
            tint.setAlpha(38 if isDarkTheme() else 30)
            painter.setPen(Qt.NoPen)
            painter.setBrush(tint)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 9, 9)
        painter.setPen(QPen(QColor(255, 255, 255, 28) if isDarkTheme() else QColor(0, 0, 0, 22), 1))
        if self.edge_left:
            painter.drawLine(0, 8, 0, self.height() - 8)
        if self.edge_top:
            painter.drawLine(8, 0, self.width() - 8, 0)


class DashboardPage(QWidget):
    """Scheda iniziale: azioni rapide e un riquadro per ogni scheda dell'app con un
    riassunto; il click su un riquadro apre la scheda corrispondente."""

    tile_clicked = Signal(str)
    add_member_requested = Signal()
    add_event_requested = Signal()
    backup_requested = Signal()
    maintenance_clicked = Signal()

    def __init__(
        self,
        get_conn: Callable,
        get_notes_text: Callable[[], str],
        get_last_backup: Callable[[], str | None],
        parent=None,
    ):
        super().__init__(parent)
        self.get_conn = get_conn
        self.get_notes_text = get_notes_text
        self.get_last_backup = get_last_backup
        self._columns = 0

        content = QWidget()
        content.setObjectName("dashboardContent")
        content.setStyleSheet("#dashboardContent { background: transparent; }")
        scroll = ScrollArea(self)
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.enableTransparentBackground()
        scroll.setFrameShape(QFrame.NoFrame)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        # Un banner per manutenzione: di norma uno solo (nascosto se non c'è niente), se ce ne sono di
        # più (es. una ordinaria in corso e una temporanea annunciata per domani) si impilano.
        self._banner_box = QVBoxLayout()
        self._banner_box.setSpacing(8)
        self._maintenance_banner = MaintenanceBanner(self)
        self._maintenance_banner.clicked.connect(self.maintenance_clicked)
        self._banner_box.addWidget(self._maintenance_banner)
        self._extra_banners: list[MaintenanceBanner] = []
        layout.addLayout(self._banner_box)

        actions = QHBoxLayout()
        add_member = PrimaryPushButton(FIF.ADD, tr("button.add_member"), self)
        add_member.clicked.connect(self.add_member_requested)
        add_event = PushButton(FIF.CALENDAR, tr("calendar.add"), self)
        add_event.clicked.connect(self.add_event_requested)
        backup = PushButton(FIF.SAVE, tr("backup.create_now"), self)
        backup.clicked.connect(self.backup_requested)
        for button in (add_member, add_event, backup):
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)

        # La copertina: una scheda sola con in alto logo, numeri e grafico (CoverHero) e sotto le quattro sezioni
        # cliccabili. I riquadri di ex membri e bannati sono dentro il CoverHero.
        self._cover = CoverCard(self)
        cover_layout = QVBoxLayout(self._cover)
        cover_layout.setContentsMargins(0, 0, 0, 0)
        cover_layout.setSpacing(0)
        self._hero = CoverHero(self._cover)
        self._cover.hero = self._hero
        self._hero.zone_clicked.connect(self.tile_clicked)
        cover_layout.addWidget(self._hero)
        self._band = QWidget(self._cover)
        self._band_grid = QGridLayout(self._band)
        self._band_grid.setContentsMargins(6, 4, 6, 6)
        self._band_grid.setSpacing(0)
        cover_layout.addWidget(self._band)
        self._tiles: dict[str, CoverSection] = {}
        for key, icon, title in [
            (TILE_CALENDAR, FIF.CALENDAR, tr("nav.calendar")),
            (TILE_BDO, FIF.GLOBE, tr("nav.bdo")),
            (TILE_NOTES, FIF.QUICK_NOTE, tr("nav.notes")),
            (TILE_SETTINGS, FIF.SETTING, tr("nav.settings")),
        ]:
            tile = CoverSection(icon, title, self._band)
            tile.clicked.connect(lambda k=key: self.tile_clicked.emit(k))
            self._tiles[key] = tile
        layout.addWidget(self._cover)
        # Gli stessi nomi di prima per logo e auguri (li usano i temi stagionali): ora sono nella copertina.
        self._wordmark = self._hero.wordmark
        self._greeting = self._hero.greeting
        self._greeting_icon = self._hero.greeting_icon
        if WORDMARK_PATH.exists():
            self._wordmark.setPixmap(QPixmap(str(WORDMARK_PATH)).scaledToHeight(WORDMARK_HEIGHT, Qt.SmoothTransformation))
        else:
            self._wordmark.hide()
        # I numeri salgono da zero la prima volta che la dashboard compare (vedi showEvent).
        self._intro_pending = True

        # Divisione netta tra i riquadri delle schede (sopra) e le informazioni generali (sotto).
        layout.addSpacing(14)
        divider = QFrame(self)
        divider.setFrameShape(QFrame.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: rgba(0, 0, 0, 55); border: none;")
        layout.addWidget(divider)
        layout.addWidget(StrongBodyLabel(tr("dash.divider"), self))

        self._info_grid = QGridLayout()
        self._info_grid.setSpacing(16)
        self._info_cards: dict[str, InfoCard] = {}
        for key, icon, title in [
            ("info_joins", FIF.SYNC, tr("dash.recent_movements")),
            ("info_birthdays", FIF.HEART, tr("dash.birthdays")),
            ("info_anniversaries", FIF.CALENDAR, tr("dash.anniversaries")),
            ("info_timers", FIF.GLOBE, tr("dash.bdo_timers")),
        ]:
            self._info_cards[key] = InfoCard(icon, title, self)
        layout.addLayout(self._info_grid)
        # Tema stagionale: gruppo di decorazioni (zucche, palline...) sotto i riquadri delle informazioni, al centro,
        # e strato con le decorazioni degli angoli. Senza tema restano nascosti.
        self._cluster = QLabel(self)
        self._cluster.hide()
        layout.addWidget(self._cluster, 0, Qt.AlignHCenter)
        layout.addStretch(1)
        self._decor = DecorOverlay(content, DASHBOARD_DECOR)  # sul contenuto: scorre via con la pagina
        self._info_columns = 1
        self._cover_layout_key = None
        self._reflow(1)
        self.set_bdo("", None, [tr("server.error.no_key")])
        self.set_timers([])

    # -- tema stagionale -----------------------------------------------------
    def set_wordmark(self, path: Path) -> None:
        if self._wordmark is not None and path.exists():
            self._wordmark.setPixmap(QPixmap(str(path)).scaledToHeight(WORDMARK_HEIGHT, Qt.SmoothTransformation))

    def set_greeting(self, text: str | None, color: str = "", icon_path: Path | None = None) -> None:
        """Scritta sotto il titolo "Dashboard", con una piccola icona se c'è; None la nasconde."""
        self._greeting.setVisible(bool(text))
        has_icon = bool(text) and icon_path is not None and icon_path.exists()
        self._greeting_icon.setVisible(has_icon)
        if has_icon:
            size = GREETING_ICON_SIZE
            self._greeting_icon.setPixmap(
                QPixmap(str(icon_path)).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        if text:
            self._greeting.setText(text)
            self._greeting.setStyleSheet(
                f"font-family: {FONT_FAMILY}; font-weight: 600; font-size: 15px;" + (f" color: {color};" if color else "")
            )

    def set_decor(self, season) -> None:
        """Decorazioni del tema (None = nessuna): angoli sopra la pagina e gruppo sotto i riquadri."""
        self._decor.set_season(season)
        path = season.decor_path("cluster") if season is not None else None
        if path is not None and path.exists():
            self._cluster.setPixmap(QPixmap(str(path)).scaledToWidth(CLUSTER_WIDTH, Qt.SmoothTransformation))
        else:
            self._cluster.clear()
        self._place_cluster()

    def _place_cluster(self) -> None:
        """Il gruppo di decorazioni si vede solo se il tema ne ha uno."""
        self._cluster.setVisible(self._cluster.pixmap() is not None and not self._cluster.pixmap().isNull())

    # -- layout -----------------------------------------------------------
    def _reflow(self, columns: int) -> None:
        if columns == self._columns:
            return
        self._columns = columns
        info_columns = max(1, min(columns, len(self._info_cards)))
        for card in self._info_cards.values():
            self._info_grid.removeWidget(card)
        for index, card in enumerate(self._info_cards.values()):
            self._info_grid.addWidget(card, index // info_columns, index % info_columns)
        for col in range(MAX_COLUMNS):
            self._info_grid.setColumnStretch(col, 1 if col < info_columns else 0)
        self._info_columns = info_columns

    def _reflow_cover(self, width: int) -> None:
        """Copertina: il grafico accanto ai numeri solo se la pagina è larga; le quattro sezioni in basso su una
        fila o su due."""
        wide = width >= COVER_WIDE_WIDTH
        band_columns = 4 if width >= COVER_BAND_WIDE_WIDTH else 2
        key = (wide, band_columns)
        if key == self._cover_layout_key:
            return
        self._cover_layout_key = key
        self._hero.set_wide(wide)
        for tile in self._tiles.values():
            self._band_grid.removeWidget(tile)
        for index, tile in enumerate(self._tiles.values()):
            row, column = divmod(index, band_columns)
            tile.edge_left, tile.edge_top = column > 0, row > 0
            self._band_grid.addWidget(tile, row, column)
            tile.update()
        for column in range(4):
            self._band_grid.setColumnStretch(column, 1 if column < band_columns else 0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reflow(max(1, min(MAX_COLUMNS, (self.width() - 48) // TILE_MIN_WIDTH)))
        self._reflow_cover(self.width())

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._intro_pending:
            self._intro_pending = False
            self._hero.play_count_up()

    # -- contenuto ----------------------------------------------------------
    def refresh(self) -> None:
        conn = self.get_conn()
        today = date.today()
        counts = stats.counts_by_status(conn)
        self._hero.set_data(
            counts[STATUS_ATTIVO], counts[STATUS_EX_MEMBRO], counts[STATUS_BANNATO], guild_capacity(conn),
            queries.joined_recently(conn), queries.transitions_to(conn, STATUS_EX_MEMBRO),
            queries.transitions_to(conn, STATUS_BANNATO),
            queries.monthly_turnover(conn, today), queries.membership_trend(conn, today),
            queries.tenure_distribution(conn, today), queries.tracking_start(conn),
        )

        agenda = queries.upcoming_agenda(conn, date.today())
        if agenda:
            agenda_lines = [tr("dash.next_days", n=queries.AGENDA_DAYS)]
            highlighted = set()
            for day, title, is_holiday in agenda[:4]:
                tag = f" ({tr('dash.holiday')})" if is_holiday else ""
                if day == date.today():
                    highlighted.add(len(agenda_lines))
                agenda_lines.append((day_text(day, date.today(), day.strftime("%d-%m")), f"{title}{tag}"))
            events_count = str(sum(1 for _, _, holiday in agenda if not holiday))
            self._tiles[TILE_CALENDAR].set_content(events_count, agenda_lines, today_lines=frozenset(highlighted))
        else:
            self._tiles[TILE_CALENDAR].set_content("", [tr("dash.no_events")])

        notes = [line.strip() for line in self.get_notes_text().splitlines() if line.strip()]
        preview = [line if len(line) <= 60 else line[:57] + "..." for line in notes[:NOTES_PREVIEW_LINES]]
        self._tiles[TILE_NOTES].set_content("", preview or [tr("dash.notes_empty")])

        activity = queries.recent_movements(conn, INFO_ROWS)
        self._info_cards["info_joins"].set_content(
            "",
            [
                (
                    day_text(date.fromisoformat(r["day"]), date.today(), iso_to_display(r["day"])),
                    r["family_name"] + (f" ({r['main_name']})" if r["main_name"] else ""),
                    (tr(f"chip.{r['kind']}"), MOVE_TONES[r["kind"]]),
                )
                for r in activity
            ]
            or [tr("dash.no_joins")],
        )
        birthday_lines = []
        birthday_today = set()
        birthday_colors: dict[int, str] = {}
        for day, family, main, age, status in stats.upcoming_birthdays(
            conn, today, days=BIRTHDAY_DAYS, limit=INFO_ROWS, include_former=True
        ):
            name = family + (f" ({main})" if main else "")
            age_text = tr("dash.birthday_age", age=age) if age else ""
            if day == today:
                birthday_today.add(len(birthday_lines))
                if status == STATUS_EX_MEMBRO:
                    birthday_colors[len(birthday_lines)] = FORMER_TODAY_COLOR
            former = (tr("chip.former"), TONE_OUTLINE) if status == STATUS_EX_MEMBRO else None
            birthday_lines.append((day_text(day, today, day.strftime("%d-%m")), f"{name}{age_text}", former))
        self._info_cards["info_birthdays"].set_content(
            "",
            birthday_lines or [tr("dash.no_birthdays")],
            today_lines=frozenset(birthday_today),
            today_colors=birthday_colors,
        )

        anniversaries = stats.upcoming_anniversaries(conn, today, days=ANNIVERSARY_DAYS, limit=INFO_ROWS)
        self._info_cards["info_anniversaries"].set_content(
            "",
            [
                (
                    day_text(day, today, day.strftime("%d-%m")),
                    f"{family + (f' ({main})' if main else '')} — {years} "
                    f"{tr('dash.year_one') if years == 1 else tr('dash.year_many')}",
                )
                for day, family, main, years in anniversaries
            ]
            or [tr("dash.no_anniversaries")],
            today_lines=frozenset(i for i, (day, *_rest) in enumerate(anniversaries) if day == today),
        )

        last_backup = self.get_last_backup()
        self._tiles[TILE_SETTINGS].set_content(
            "",
            [
                tr("dash.version", version=__version__),
                tr("dash.backup_last", when=last_backup) if last_backup else tr("dash.backup_none"),
            ],
        )

    def set_timers(self, lines: list[str]) -> None:
        self._info_cards["info_timers"].set_content("", lines or [tr("server.error.no_key")])

    def set_bdo(self, value: str, color: str | None, lines: list[str], announce_color: str | None = None) -> None:
        """announce_color: colore dell'ultima riga (manutenzione annunciata), in evidenza."""
        if announce_color and len(lines) > 1:
            last = len(lines) - 1  # l'annuncio è sempre l'ultima riga
            self._tiles[TILE_BDO].set_content(
                value, lines, color, today_lines=frozenset({last}), today_colors={last: announce_color}
            )
        else:
            self._tiles[TILE_BDO].set_content(value, lines, color)

    def set_maintenance_banner(self, text: str | None, color: str | None = None) -> None:
        self._maintenance_banner.set_text(text, color)

    def set_extra_maintenance_banners(self, banners: list[tuple[str, str]]) -> None:
        """Banner sotto il primo, uno per ogni altra manutenzione (testo, colore)."""
        while len(self._extra_banners) < len(banners):
            banner = MaintenanceBanner(self)
            banner.clicked.connect(self.maintenance_clicked)
            self._banner_box.addWidget(banner)
            self._extra_banners.append(banner)
        for index, banner in enumerate(self._extra_banners):
            if index < len(banners):
                banner.set_text(*banners[index])
            else:
                banner.set_text(None)
