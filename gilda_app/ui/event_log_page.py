"""Scheda "Registro eventi": lo storico delle operazioni fatte nel programma, il più recente in alto.

Verde chi entra in gilda o torna tra i membri attuali, rosso chi esce (ex membro o bannato); le altre
operazioni (cambi di nome, modifiche, correzioni dello storico, import...) senza colore. I testi si
costruiscono qui da tipo e dettagli salvati (vedi db/event_log.py), così seguono la lingua del programma."""
from datetime import date, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QHeaderView, QTableWidgetItem, QVBoxLayout, QWidget
from qfluentwidgets import CaptionLabel, CheckBox, ComboBox, SubtitleLabel, TableWidget

from gilda_app.db import event_log
from gilda_app.i18n import tr
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO, status_label
from gilda_app.ui.persistent_clear_search import PersistentClearSearchLineEdit
from gilda_app.ui.season_decor import DecorItem, DecorOverlay, snow, OrnamentedPage
from gilda_app.utils.date_format import iso_to_display
from gilda_app.utils.scrollbar import widen_scrollbar_on_hover

TABLE_FONT = QFont("Segoe UI", 13)
HEADER_FONT = QFont("Segoe UI", 13, QFont.DemiBold)
COLOR_GOOD = QColor("#d7f0dc")  # come l'ingresso nello storico del membro
COLOR_BAD = QColor("#f8d4d4")  # come il ban nello storico del membro
TEXT_COLOR = QColor("#1f1f1f")
WHEN_COLUMN, EVENT_COLUMN, MEMBER_COLUMN, DETAIL_COLUMN = range(4)
FILTER_ALL, FILTER_GOOD, FILTER_BAD, FILTER_OTHER = "all", "good", "bad", "other"
RECENT_DAYS = 60  # di norma si vedono solo gli ultimi giorni: "Mostra tutto" e la ricerca arrivano a ogni evento
MAX_VALUE_CHARS = 40  # i valori lunghi (una nota) si accorciano nel dettaglio di una modifica
EMPTY = "—"

FIELD_LABELS = {
    "family_name": "label.family_name",
    "main_name": "label.main_name",
    "discord_name": "label.discord_name",
    "nations": "column.nation",
    "note": "label.note",
    "data_inserimento": "log.field.joined_on",
    "birthday": "label.birthday",
    "still_on_discord": "column.still_on_discord",
}


def _short(value: str) -> str:
    value = (value or "").replace("\n", " ").strip()
    if not value:
        return EMPTY
    return value if len(value) <= MAX_VALUE_CHARS else value[: MAX_VALUE_CHARS - 1] + "…"


def _value(field: str, value: str) -> str:
    if field == "still_on_discord":
        return tr("log.yes") if value else tr("log.no")
    if field == "data_inserimento" and value:
        return iso_to_display(value)
    return _short(value)


def _changes_text(detail: dict) -> str:
    parts = []
    for change in detail.get("changes", []):
        field = change.get("field", "")
        label = tr(FIELD_LABELS[field]) if field in FIELD_LABELS else field
        parts.append(f"{label}: {_value(field, change.get('old', ''))} → {_value(field, change.get('new', ''))}")
    return "; ".join(parts)


def event_label(row) -> str:
    """Nome breve dell'evento: la colonna "Evento"."""
    kind, previous, new = row["kind"], row["from_status"], row["to_status"]
    if kind == event_log.KIND_ADDED:
        return tr("log.kind.join") if new == STATUS_ATTIVO else tr("log.kind.added")
    if kind == event_log.KIND_STATUS:
        if new == STATUS_ATTIVO:
            return tr("log.kind.rejoin")
        if new == STATUS_EX_MEMBRO and previous == STATUS_ATTIVO:
            return tr("log.kind.left")
        if new == STATUS_BANNATO:
            return tr("log.kind.banned")
        return tr("log.kind.moved")
    if kind == event_log.KIND_SYSTEM:
        return tr(f"log.system.{event_log.event_detail(row).get('what', 'other')}.label")
    return tr(f"log.kind.{kind}")


def event_details(row) -> str:
    """Il dettaglio dell'evento: la colonna "Dettagli"."""
    kind, previous, new = row["kind"], row["from_status"], row["to_status"]
    detail = event_log.event_detail(row)
    if kind == event_log.KIND_ADDED:
        text = tr("log.detail.added_to", status=status_label(new)) if new else ""
        if detail.get("joined"):
            text += (" · " if text else "") + tr("log.detail.joined_on", date=iso_to_display(detail["joined"]))
        return text
    if kind == event_log.KIND_STATUS:
        text = f"{status_label(previous)} → {status_label(new)}" if previous else status_label(new)
        if detail.get("note"):
            text += " · " + tr("log.detail.note", note=_short(detail["note"]))
        return text
    if kind in (event_log.KIND_NAME, event_log.KIND_EDIT):
        return _changes_text(detail)
    if kind == event_log.KIND_DELETE:
        return tr("log.detail.deleted_from", status=status_label(previous)) if previous else ""
    if kind == event_log.KIND_HISTORY:
        return tr(f"log.history.{detail.get('what', 'status_entry')}")
    if kind == event_log.KIND_SYSTEM:
        what = detail.get("what", "other")
        return tr(f"log.system.{what}", **{k: v for k, v in detail.items() if k != "what"})
    return ""


def event_when(at: str) -> str:
    """Data e ora come "28-10-2026 14:35"; senza l'ora se è solo una data (eventi recuperati dallo storico)."""
    day = iso_to_display(at)
    time = at[11:16]
    return day if not time or at[11:19] == "00:00:00" else f"{day} {time}"


def filter_matches(row, mode: str) -> bool:
    if mode == FILTER_ALL:
        return True
    tone = event_log.tone(row)
    if mode == FILTER_GOOD:
        return tone == event_log.TONE_GOOD
    if mode == FILTER_BAD:
        return tone == event_log.TONE_BAD
    return tone == event_log.TONE_NEUTRAL


class EventLogPage(OrnamentedPage, QWidget):
    member_requested = Signal(int)  # doppio click su una riga di un membro che esiste ancora

    def __init__(self, get_conn, parent=None):
        super().__init__(parent)
        self.get_conn = get_conn
        self._events: list = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        header = QHBoxLayout()
        header.addWidget(SubtitleLabel(tr("nav.log"), self))
        # Ornamento del tema stagionale, accanto al titolo (a destra ci sono filtro e ricerca).
        self._decor = DecorOverlay(self, [DecorItem(("page_log", "page_b"), height=56, left=230, top=12, min_page_width=1000), *snow(left=300)])
        header.addStretch(1)
        self.show_all = CheckBox(tr("log.show_all", days=RECENT_DAYS), self)
        self.show_all.stateChanged.connect(self._apply_filter)
        header.addWidget(self.show_all)
        self.filter_box = ComboBox(self)
        for mode, key in (
            (FILTER_ALL, "log.filter.all"),
            (FILTER_GOOD, "log.filter.good"),
            (FILTER_BAD, "log.filter.bad"),
            (FILTER_OTHER, "log.filter.other"),
        ):
            self.filter_box.addItem(tr(key), userData=mode)
        self.filter_box.currentIndexChanged.connect(self._apply_filter)
        header.addWidget(self.filter_box)
        self.search_box = PersistentClearSearchLineEdit(self)
        self.search_box.setPlaceholderText(tr("log.search"))
        self.search_box.setFixedWidth(300)
        self.search_box.textChanged.connect(self._apply_filter)
        header.addWidget(self.search_box)
        layout.addLayout(header)

        hint = CaptionLabel(tr("log.hint"), self)
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self._older_note = CaptionLabel("", self)
        layout.addWidget(self._older_note)
        self._older_note.hide()

        self.table = TableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            [tr("log.column.when"), tr("log.column.event"), tr("log.column.member"), tr("log.column.details")]
        )
        self.table.setFont(TABLE_FONT)
        self.table.horizontalHeader().setFont(HEADER_FONT)
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setWordWrap(False)
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(WHEN_COLUMN, QHeaderView.Fixed)
        header_view.setSectionResizeMode(EVENT_COLUMN, QHeaderView.Fixed)
        header_view.setSectionResizeMode(MEMBER_COLUMN, QHeaderView.Interactive)
        header_view.setStretchLastSection(True)
        self.table.setColumnWidth(WHEN_COLUMN, 190)
        self.table.setColumnWidth(EVENT_COLUMN, 150)
        self.table.setColumnWidth(MEMBER_COLUMN, 230)
        self.table.doubleClicked.connect(self._on_double_click)
        widen_scrollbar_on_hover(self.table.scrollDelagate.vScrollBar)
        layout.addWidget(self.table)

        self._empty = CaptionLabel(tr("log.empty"), self)
        self._empty.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._empty)
        self._empty.hide()

    def refresh(self) -> None:
        self._events = event_log.get_events(self.get_conn())
        self._apply_filter()

    def _apply_filter(self, *_args) -> None:
        mode = self.filter_box.currentData() or FILTER_ALL
        needle = self.search_box.text().strip().casefold()
        # Di norma solo gli ultimi giorni, per tenere leggera la scheda; cercando, o con "Mostra tutto", ogni evento.
        cutoff = (date.today() - timedelta(days=RECENT_DAYS)).isoformat()
        limited = not self.show_all.isChecked() and not needle
        older = 0
        rows = []
        for event in self._events:
            if limited and event["at"][:10] < cutoff:
                older += 1
                continue
            if not filter_matches(event, mode):
                continue
            label, details = event_label(event), event_details(event)
            if needle and needle not in f"{event['member_name'] or ''} {label} {details}".casefold():
                continue
            rows.append((event, label, details))
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for index, (event, label, details) in enumerate(rows):
            tone = event_log.tone(event)
            background = {event_log.TONE_GOOD: COLOR_GOOD, event_log.TONE_BAD: COLOR_BAD}.get(tone)
            cells = (event_when(event["at"]), label, event["member_name"] or "", details)
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                if column == EVENT_COLUMN:
                    item.setFont(HEADER_FONT)
                if background is not None:
                    item.setBackground(background)
                    item.setForeground(TEXT_COLOR)
                if column == WHEN_COLUMN:
                    item.setData(Qt.UserRole, event["member_id"])
                self.table.setItem(index, column, item)
        self._empty.setVisible(not rows)
        self.table.setVisible(bool(rows))
        self._older_note.setText(tr("log.older_hidden", n=older, days=RECENT_DAYS))
        self._older_note.setVisible(older > 0)

    def _on_double_click(self, index) -> None:
        item = self.table.item(index.row(), WHEN_COLUMN)
        member_id = item.data(Qt.UserRole) if item is not None else None
        if member_id is not None:
            self.member_requested.emit(int(member_id))
