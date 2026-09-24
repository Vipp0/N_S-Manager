import html
from datetime import date, datetime, timezone

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import CardWidget, CaptionLabel, FluentIcon as FIF, PushButton, StrongBodyLabel, SubtitleLabel

from gilda_app.i18n import tr
from gilda_app.ui.server_status_footer import COLOR_MAINTENANCE, COLOR_UNKNOWN, describe_error, describe_region
from gilda_app.utils.bdo_news import NewsItem, upcoming_maintenance
from gilda_app.utils.bdo_timers import (
    BOSS_ROWS_LIMIT,
    RESET_KEYS,
    BossTimers,
    ResetTimers,
    countdown_text,
    upcoming_bosses,
)
from gilda_app.utils.server_status import REGIONS, RegionStatus


def _local_time(when: datetime, now: datetime) -> str:
    """Ora nel fuso del computer; con la data se non è oggi."""
    local = when.astimezone()
    return local.strftime("%H:%M") if local.date() == now.astimezone().date() else local.strftime("%d-%m %H:%M")


def timer_summary_lines(resets: ResetTimers | None, bosses: BossTimers | None, now: datetime) -> list[str]:
    """Poche righe per la dashboard: prossimo boss, reset giornaliero, consegna imperiale."""
    lines = []
    if bosses is not None:
        upcoming = upcoming_bosses(bosses, now, 1)
        if upcoming:
            group = upcoming[0]
            lines.append(
                tr(
                    "dash.next_boss",
                    names=", ".join(group.names),
                    time=_local_time(group.when, now),
                    left=countdown_text(group.when, now),
                )
            )
    if resets is not None:
        for key in ("daily_reset", "imperial_delivery"):
            if key in resets.resets:
                lines.append(f"{tr('timer.' + key)}: {countdown_text(resets.resets[key], now)}")
    return lines


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

        self._resets: ResetTimers | None = None
        self._bosses: BossTimers | None = None
        self._timer_error: str | None = None
        timers_row = QHBoxLayout()
        timers_row.setSpacing(16)
        reset_card = CardWidget(self)
        reset_layout = QVBoxLayout(reset_card)
        reset_layout.addWidget(StrongBodyLabel(tr("bdo.reset_title"), reset_card))
        self._reset_label = QLabel(reset_card)
        self._reset_label.setTextFormat(Qt.RichText)
        reset_layout.addWidget(self._reset_label)
        reset_layout.addStretch(1)
        boss_card = CardWidget(self)
        boss_layout = QVBoxLayout(boss_card)
        boss_layout.addWidget(StrongBodyLabel(tr("bdo.boss_title"), boss_card))
        self._boss_label = QLabel(boss_card)
        self._boss_label.setTextFormat(Qt.RichText)
        boss_layout.addWidget(self._boss_label)
        boss_layout.addStretch(1)
        boss_layout.addWidget(CaptionLabel(tr("bdo.timers_hint"), boss_card))
        timers_row.addWidget(reset_card, 1)
        timers_row.addWidget(boss_card, 1)
        layout.addLayout(timers_row)

        news_card = CardWidget(self)
        news_layout = QVBoxLayout(news_card)
        news_layout.addWidget(StrongBodyLabel(tr("bdo.news_title"), news_card))
        self._upcoming = QLabel(news_card)
        self._upcoming.setWordWrap(True)
        news_layout.addWidget(self._upcoming)
        self._news_list = QLabel(news_card)
        self._news_list.setWordWrap(True)
        self._news_list.setTextFormat(Qt.RichText)
        self._news_list.setOpenExternalLinks(True)
        news_layout.addWidget(self._news_list)
        news_layout.addWidget(CaptionLabel(tr("bdo.news_hint"), news_card))
        layout.addWidget(news_card)
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

    def show_news(self, items: list[NewsItem]) -> None:
        upcoming = upcoming_maintenance(items, date.today())
        if upcoming is not None:
            when = upcoming.maintenance_date.strftime("%d-%m-%Y")
            self._upcoming.setText(f"<b>{html.escape(tr('bdo.news_upcoming', date=when))}</b>")
            self._upcoming.setStyleSheet(f"color: {COLOR_MAINTENANCE};")
        else:
            self._upcoming.setText(tr("bdo.news_none_upcoming"))
            self._upcoming.setStyleSheet("")
        lines = []
        for item in items:
            title = html.escape(item.title)
            if item.url:
                title = f'<a href="{html.escape(item.url, quote=True)}">{title}</a>'
            if item.is_maintenance:
                title = f'<b style="color: {COLOR_MAINTENANCE};">{title}</b>'
            posted = item.posted.strftime("%d-%m-%Y") if item.posted else ""
            lines.append(f"{posted} &nbsp; {title}")
        self._news_list.setText("<br>".join(lines))

    def show_news_error(self, kind: str) -> None:
        self._upcoming.setText(describe_error(kind)[0])
        self._upcoming.setStyleSheet("")
        self._news_list.setText("")

    # -- Timer (reset, cicli, boss) -------------------------------------------
    def set_timer_data(self, resets: ResetTimers | None, bosses: BossTimers | None, error: str | None) -> None:
        self._resets, self._bosses, self._timer_error = resets, bosses, error
        self.render_timers()

    def render_timers(self) -> None:
        """Ridisegna i conti alla rovescia dagli orari assoluti in cache: chiamato ogni
        mezzo minuto, così restano esatti tra un aggiornamento dall'API e il successivo."""
        now = datetime.now(timezone.utc)
        if self._timer_error and self._resets is None and self._bosses is None:
            self._reset_label.setText(html.escape(describe_error(self._timer_error)[0]))
            self._boss_label.setText("")
            return

        rows = []
        if self._resets is not None:
            for key in RESET_KEYS:
                when = self._resets.resets.get(key)
                if when is not None:
                    rows.append((tr(f"timer.{key}"), countdown_text(when, now)))
            if self._resets.cycle_change is not None:
                night = (self._resets.cycle or "").lower() == "night"
                cycle_text = tr("timer.cycle_night" if night else "timer.cycle_day", time=countdown_text(self._resets.cycle_change, now))
                rows.append((tr("timer.cycle_label"), cycle_text))
        self._reset_label.setText(
            "<table cellspacing='4'>"
            + "".join(f"<tr><td>{html.escape(a)}</td><td>&nbsp;&nbsp;<b>{html.escape(b)}</b></td></tr>" for a, b in rows)
            + "</table>"
        )

        lines = []
        if self._bosses is not None:
            for group in upcoming_bosses(self._bosses, now, BOSS_ROWS_LIMIT):
                left = html.escape(tr("bdo.boss_in", time=countdown_text(group.when, now)))
                lines.append(
                    f"<b>{_local_time(group.when, now)}</b> &nbsp; {html.escape(', '.join(group.names))}"
                    f" &nbsp; <span style='color: #8a8886;'>{left}</span>"
                )
            if self._bosses.previous_names and self._bosses.previous_when is not None:
                previous = tr(
                    "bdo.boss_previous",
                    names=", ".join(self._bosses.previous_names),
                    time=_local_time(self._bosses.previous_when, now),
                )
                lines.append(f"<span style='color: #8a8886;'>{html.escape(previous)}</span>")
        self._boss_label.setText("<br>".join(lines))
