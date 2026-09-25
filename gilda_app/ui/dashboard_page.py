import html
from datetime import date
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    FluentIcon as FIF,
    PrimaryPushButton,
    PushButton,
    ScrollArea,
    StrongBodyLabel,
    SubtitleLabel,
    isDarkTheme,
)

from gilda_app.db import dashboard as queries
from gilda_app.db import stats
from gilda_app.db.database import get_members
from gilda_app.i18n import tr
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO, status_label
from gilda_app.utils.date_format import iso_to_display, relative_day_label
from gilda_app.utils.flags import display_nation
from gilda_app.utils.icons import ban_icon
from gilda_app.version import __version__

TILE_MIN_WIDTH = 300
MAX_COLUMNS = 4
NOTES_PREVIEW_LINES = 3

# Chiavi dei riquadri diversi dalle tre liste membri (le liste usano il loro status).
TILE_STATS = "stats"
TILE_CALENDAR = "calendar"
TILE_BDO = "bdo"
TILE_NOTES = "notes"
TILE_SETTINGS = "settings"

WORDMARK_PATH = Path(__file__).resolve().parent.parent / "resources" / "wordmark.png"
WORDMARK_HEIGHT = 86
TILE_KEYS_INFO = ("info_joins", "info_anniversaries", "info_nations")

_VALUE_STYLE = "font-size: 28px; font-weight: 600;"
# Le righe che riguardano oggi (eventi, festività, compleanni, anniversari): grassetto e
# un colore caldo, così si distinguono da quelle dei giorni successivi.
TODAY_COLOR = "#b45309"


def day_text(day: date, today: date, fallback: str) -> str:
    """"Oggi" / "Domani" / "Ieri" per i giorni vicini, altrimenti la data (fallback)."""
    key = relative_day_label(day, today)
    return tr(key) if key else fallback


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
        layout.addWidget(self._value)
        self._lines = BodyLabel(self)
        self._lines.setWordWrap(True)
        self._lines.setTextFormat(Qt.RichText)
        layout.addWidget(self._lines)
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
        self, value: str, lines: list[str], value_color: str | None = None, today_lines: frozenset[int] = frozenset()
    ) -> None:
        """today_lines: indici delle righe da evidenziare perché riguardano oggi."""
        self._value.setText(value)
        self._value.setVisible(bool(value))
        self._value.setStyleSheet(_VALUE_STYLE + (f" color: {value_color};" if value_color else ""))
        rendered = []
        for index, line in enumerate(lines):
            text = html.escape(line)
            if index in today_lines:
                text = f'<b style="color: {TODAY_COLOR};">{text}</b>'
            rendered.append(text)
        self._lines.setText("<br>".join(rendered))


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


class DashboardPage(QWidget):
    """Scheda iniziale: azioni rapide e un riquadro per ogni scheda dell'app con un
    riassunto; il click su un riquadro apre la scheda corrispondente."""

    tile_clicked = Signal(str)
    add_member_requested = Signal()
    add_event_requested = Signal()
    backup_requested = Signal()

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
        header = QHBoxLayout()
        header.addWidget(SubtitleLabel(tr("nav.dashboard"), self))
        header.addStretch(1)
        # Wordmark al centro dell'intestazione, come nelle liste dei membri.
        if WORDMARK_PATH.exists():
            wordmark = QLabel(self)
            wordmark.setPixmap(QPixmap(str(WORDMARK_PATH)).scaledToHeight(WORDMARK_HEIGHT, Qt.SmoothTransformation))
            header.addWidget(wordmark)
        header.addStretch(1)
        layout.addLayout(header)

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

        self._grid = QGridLayout()
        self._grid.setSpacing(16)
        self._tiles: dict[str, DashboardTile] = {}
        tile_defs = [
            (STATUS_ATTIVO, FIF.PEOPLE, status_label(STATUS_ATTIVO)),
            (STATUS_EX_MEMBRO, FIF.HISTORY, status_label(STATUS_EX_MEMBRO)),
            (STATUS_BANNATO, ban_icon(), status_label(STATUS_BANNATO)),
            (TILE_STATS, FIF.PIE_SINGLE, tr("nav.stats")),
            (TILE_CALENDAR, FIF.CALENDAR, tr("nav.calendar")),
            (TILE_BDO, FIF.GLOBE, tr("nav.bdo")),
            (TILE_NOTES, FIF.QUICK_NOTE, tr("nav.notes")),
            (TILE_SETTINGS, FIF.SETTING, tr("nav.settings")),
        ]
        for key, icon, title in tile_defs:
            tile = DashboardTile(icon, title, self)
            tile.clicked.connect(lambda k=key: self.tile_clicked.emit(k))
            self._tiles[key] = tile
        layout.addLayout(self._grid)

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
            ("info_joins", FIF.ADD, tr("dash.recent_joins")),
            ("info_birthdays", FIF.HEART, tr("dash.birthdays")),
            ("info_anniversaries", FIF.CALENDAR, tr("dash.anniversaries")),
            ("info_nations", FIF.PIE_SINGLE, tr("dash.top_nations")),
            ("info_timers", FIF.GLOBE, tr("dash.bdo_timers")),
        ]:
            self._info_cards[key] = InfoCard(icon, title, self)
        layout.addLayout(self._info_grid)
        layout.addStretch(1)
        self._reflow(1)
        self.set_bdo("", None, [tr("server.error.no_key")])
        self.set_timers([])

    # -- layout -----------------------------------------------------------
    def _reflow(self, columns: int) -> None:
        if columns == self._columns:
            return
        self._columns = columns
        for tile in self._tiles.values():
            self._grid.removeWidget(tile)
        for index, tile in enumerate(self._tiles.values()):
            self._grid.addWidget(tile, index // columns, index % columns)
        for col in range(MAX_COLUMNS):
            self._grid.setColumnStretch(col, 1 if col < columns else 0)
        info_columns = max(1, min(columns, len(self._info_cards)))
        for card in self._info_cards.values():
            self._info_grid.removeWidget(card)
        for index, card in enumerate(self._info_cards.values()):
            self._info_grid.addWidget(card, index // info_columns, index % info_columns)
        for col in range(MAX_COLUMNS):
            self._info_grid.setColumnStretch(col, 1 if col < info_columns else 0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reflow(max(1, min(MAX_COLUMNS, (self.width() - 48) // TILE_MIN_WIDTH)))

    # -- contenuto ----------------------------------------------------------
    def refresh(self) -> None:
        conn = self.get_conn()
        for status, recent_count, recent_key in (
            (STATUS_ATTIVO, queries.joined_recently(conn), "dash.joined_30"),
            (STATUS_EX_MEMBRO, queries.transitions_to(conn, STATUS_EX_MEMBRO), "dash.left_30"),
            (STATUS_BANNATO, queries.transitions_to(conn, STATUS_BANNATO), "dash.banned_30"),
        ):
            self._tiles[status].set_content(
                str(len(get_members(conn, status))), [tr(recent_key, n=recent_count)]
            )

        movements = queries.recent_transitions(conn)
        lines = [
            f"{day_text(date.fromisoformat(row['changed_at'][:10]), date.today(), iso_to_display(row['changed_at']))}"
            f"  {row['family_name']} → {status_label(row['new_status'])}"
            for row in movements
        ]
        self._tiles[TILE_STATS].set_content("", lines or [tr("dash.no_movements")])

        agenda = queries.upcoming_agenda(conn, date.today())
        if agenda:
            agenda_lines = [tr("dash.next_days", n=queries.AGENDA_DAYS)]
            highlighted = set()
            for day, title, is_holiday in agenda[:4]:
                tag = f" ({tr('dash.holiday')})" if is_holiday else ""
                if day == date.today():
                    highlighted.add(len(agenda_lines))
                agenda_lines.append(f"{day_text(day, date.today(), day.strftime('%d-%m'))}  {title}{tag}")
            events_count = str(sum(1 for _, _, holiday in agenda if not holiday))
            self._tiles[TILE_CALENDAR].set_content(events_count, agenda_lines, today_lines=frozenset(highlighted))
        else:
            self._tiles[TILE_CALENDAR].set_content("", [tr("dash.no_events")])

        notes = [line.strip() for line in self.get_notes_text().splitlines() if line.strip()]
        preview = [line if len(line) <= 60 else line[:57] + "..." for line in notes[:NOTES_PREVIEW_LINES]]
        self._tiles[TILE_NOTES].set_content("", preview or [tr("dash.notes_empty")])

        joins = queries.recent_joins(conn)
        self._info_cards["info_joins"].set_content(
            "",
            [
                f"{day_text(date.fromisoformat(r['data_inserimento'][:10]), date.today(), iso_to_display(r['data_inserimento']))}"
                f"  {r['family_name']}"
                + (f" ({r['main_name']})" if r["main_name"] else "")
                for r in joins
            ]
            or [tr("dash.no_joins")],
        )
        today = date.today()
        birthday_lines = []
        birthday_today = set()
        for day, family, main, age in stats.upcoming_birthdays(conn, today, days=14, limit=6):
            name = family + (f" ({main})" if main else "")
            age_text = tr("dash.birthday_age", age=age) if age else ""
            if day == today:
                birthday_today.add(len(birthday_lines))
            birthday_lines.append(
                tr("dash.birthday_line", date=day_text(day, today, day.strftime("%d-%m")), name=name, age=age_text)
            )
        self._info_cards["info_birthdays"].set_content(
            "", birthday_lines or [tr("dash.no_birthdays")], today_lines=frozenset(birthday_today)
        )

        anniversaries = stats.upcoming_anniversaries(conn, today, days=30, limit=5)
        self._info_cards["info_anniversaries"].set_content(
            "",
            [
                tr(
                    "dash.anniversary_line",
                    date=day_text(day, today, day.strftime("%d-%m")),
                    name=family + (f" ({main})" if main else ""),
                    years=years,
                    unit=tr("dash.year_one") if years == 1 else tr("dash.year_many"),
                )
                for day, family, main, years in anniversaries
            ]
            or [tr("dash.no_anniversaries")],
            today_lines=frozenset(i for i, (day, *_rest) in enumerate(anniversaries) if day == today),
        )
        nations = stats.nation_distribution(conn)[:5]
        self._info_cards["info_nations"].set_content(
            "", [f"{display_nation(r['nation'])} — {r['cnt']}" for r in nations] or [tr("stats.no_data")]
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

    def set_bdo(self, value: str, color: str | None, lines: list[str]) -> None:
        self._tiles[TILE_BDO].set_content(value, lines, color)
