from datetime import date
from typing import Callable

from PySide6.QtCore import Qt, Signal
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
)

from gilda_app.db import dashboard as queries
from gilda_app.db.database import get_members
from gilda_app.i18n import tr
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO, status_label
from gilda_app.utils.date_format import iso_to_display
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

_VALUE_STYLE = "font-size: 28px; font-weight: 600;"


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
        self._lines.setTextFormat(Qt.PlainText)
        layout.addWidget(self._lines)
        layout.addStretch(1)
        self.setCursor(Qt.PointingHandCursor)

    def set_content(self, value: str, lines: list[str], value_color: str | None = None) -> None:
        self._value.setText(value)
        self._value.setVisible(bool(value))
        self._value.setStyleSheet(_VALUE_STYLE + (f" color: {value_color};" if value_color else ""))
        self._lines.setText("\n".join(lines))


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
        layout.addWidget(SubtitleLabel(tr("nav.dashboard"), self))

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
        layout.addStretch(1)
        self._reflow(1)
        self.set_bdo("", None, [tr("server.error.no_key")])

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
            f"{iso_to_display(row['changed_at'])}  {row['family_name']} → {status_label(row['new_status'])}"
            for row in movements
        ]
        self._tiles[TILE_STATS].set_content("", lines or [tr("dash.no_movements")])

        agenda = queries.upcoming_agenda(conn, date.today())
        if agenda:
            agenda_lines = [tr("dash.next_days", n=queries.AGENDA_DAYS)]
            for day, title, is_holiday in agenda[:4]:
                tag = f" ({tr('dash.holiday')})" if is_holiday else ""
                agenda_lines.append(f"{day.strftime('%d-%m')}  {title}{tag}")
            events_count = str(sum(1 for _, _, holiday in agenda if not holiday))
            self._tiles[TILE_CALENDAR].set_content(events_count, agenda_lines)
        else:
            self._tiles[TILE_CALENDAR].set_content("", [tr("dash.no_events")])

        notes = [line.strip() for line in self.get_notes_text().splitlines() if line.strip()]
        preview = [line if len(line) <= 60 else line[:57] + "..." for line in notes[:NOTES_PREVIEW_LINES]]
        self._tiles[TILE_NOTES].set_content("", preview or [tr("dash.notes_empty")])

        last_backup = self.get_last_backup()
        self._tiles[TILE_SETTINGS].set_content(
            "",
            [
                tr("dash.version", version=__version__),
                tr("dash.backup_last", when=last_backup) if last_backup else tr("dash.backup_none"),
            ],
        )

    def set_bdo(self, value: str, color: str | None, lines: list[str]) -> None:
        self._tiles[TILE_BDO].set_content(value, lines, color)
