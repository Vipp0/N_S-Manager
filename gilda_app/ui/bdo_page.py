import html
from datetime import date, datetime, timezone

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CardWidget, CaptionLabel, FluentIcon as FIF, PushButton, ScrollArea, StrongBodyLabel, SubtitleLabel

from gilda_app.i18n import tr
from gilda_app.ui.season_decor import DecorItem, DecorOverlay, snow, OrnamentedPage
from gilda_app.ui.server_status_footer import (
    COLOR_MAINTENANCE,
    COLOR_UNKNOWN,
    announced_color,
    describe_error,
    describe_region,
)
from gilda_app.utils.bdo_guild import GuildComparison, GuildInfo
from gilda_app.utils.bdo_news import NewsItem, upcoming_maintenance
from gilda_app.utils.bdo_timers import (
    BOSS_ROWS_LIMIT,
    RESET_KEYS,
    BossTimers,
    ResetTimers,
    countdown_text,
    upcoming_bosses,
)
from gilda_app.utils.server_status import DEFAULT_REGION, REGIONS, RegionStatus


GUILD_NAMES_SHOWN = 15


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


class BdoPage(OrnamentedPage, QWidget):
    """Scheda con i dati presi dall'API di bdoalerts.net. Costruita a blocchi (una card
    per funzione): oggi solo lo stato dei server, le prossime funzioni si aggiungono
    come nuove card sotto senza toccare le altre."""

    refresh_requested = Signal()
    estimate_extend_requested = Signal()
    estimate_finished_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Contenuto scorrevole: con tutte le card (stato, reset/boss, gilda, news) la
        # pagina supera facilmente l'altezza della finestra, e senza questo le news in
        # fondo restavano tagliate invece di essere raggiungibili scorrendo.
        content = QWidget()
        content.setObjectName("bdoContent")
        content.setStyleSheet("#bdoContent { background: transparent; }")
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
        layout.addWidget(SubtitleLabel(tr("bdo.title"), self))
        # Ornamento del tema stagionale: sul contenuto, così scorre via con la pagina.
        self._decor = DecorOverlay(content, [DecorItem(("page_bdo", "page_c"), height=56, right=24, top=14, min_page_width=800), *snow(right=110)])

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
        # Blocco della manutenzione in corso o annunciata: titolo con la fascia oraria e, se l'avviso lo
        # dà (di solito nelle temporanee), il motivo in evidenza. Nascosto quando non c'è niente.
        self._info_box = QWidget(status_card)
        info_layout = QVBoxLayout(self._info_box)
        info_layout.setContentsMargins(0, 8, 0, 4)
        info_layout.setSpacing(6)
        self._info_title = StrongBodyLabel("", self._info_box)
        info_layout.addWidget(self._info_title)
        self._reason_caption = CaptionLabel(tr("bdo.maintenance_reason_caption"), self._info_box)
        info_layout.addWidget(self._reason_caption)
        self._reason_frame = QFrame(self._info_box)
        self._reason_frame.setObjectName("reasonFrame")
        reason_layout = QVBoxLayout(self._reason_frame)
        reason_layout.setContentsMargins(14, 8, 12, 8)
        self._reason = BodyLabel(self._reason_frame)
        self._reason.setWordWrap(True)
        self._reason.setTextInteractionFlags(Qt.TextSelectableByMouse)
        reason_layout.addWidget(self._reason)
        info_layout.addWidget(self._reason_frame)
        self._info_box.hide()
        card_layout.addWidget(self._info_box)
        # Visibile solo durante (e poco dopo) la manutenzione stimata: vedi MainWindow._update_estimate_controls.
        self._estimate_box = QWidget(status_card)
        estimate_layout = QVBoxLayout(self._estimate_box)
        estimate_layout.setContentsMargins(0, 0, 0, 0)
        self._estimate_label = QLabel(self._estimate_box)
        self._estimate_label.setWordWrap(True)
        estimate_layout.addWidget(self._estimate_label)
        estimate_buttons = QHBoxLayout()
        self._extend_btn = PushButton(FIF.ADD, tr("bdo.estimate.extend"), self._estimate_box)
        self._extend_btn.clicked.connect(self.estimate_extend_requested)
        self._finished_btn = PushButton(FIF.ACCEPT, tr("bdo.estimate.finished"), self._estimate_box)
        self._finished_btn.clicked.connect(self.estimate_finished_requested)
        estimate_buttons.addWidget(self._extend_btn)
        estimate_buttons.addWidget(self._finished_btn)
        estimate_buttons.addStretch(1)
        estimate_layout.addLayout(estimate_buttons)
        self._estimate_box.hide()
        card_layout.addWidget(self._estimate_box)
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
        self._timers_hint = CaptionLabel("", boss_card)
        self.set_region(tr(f"region.{DEFAULT_REGION}"))
        boss_layout.addWidget(self._timers_hint)
        timers_row.addWidget(reset_card, 1)
        timers_row.addWidget(boss_card, 1)
        layout.addLayout(timers_row)

        guild_card = CardWidget(self)
        guild_layout = QVBoxLayout(guild_card)
        guild_layout.addWidget(StrongBodyLabel(tr("bdo.guild_title"), guild_card))
        self._guild_label = QLabel(guild_card)
        self._guild_label.setTextFormat(Qt.RichText)
        self._guild_label.setWordWrap(True)
        guild_layout.addWidget(self._guild_label)
        guild_layout.addWidget(CaptionLabel(tr("bdo.guild_hint"), guild_card))
        layout.addWidget(guild_card)
        self.show_guild_message(describe_error("no_key")[0])

        patch_card = CardWidget(self)
        patch_layout = QVBoxLayout(patch_card)
        patch_layout.addWidget(StrongBodyLabel(tr("bdo.patch_title"), patch_card))
        self._patch_list = QLabel(patch_card)
        self._patch_list.setWordWrap(True)
        self._patch_list.setTextFormat(Qt.RichText)
        self._patch_list.setOpenExternalLinks(True)
        patch_layout.addWidget(self._patch_list)
        patch_layout.addWidget(CaptionLabel(tr("bdo.patch_hint"), patch_card))
        layout.addWidget(patch_card)
        self.show_patch_error("no_key")

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

    def set_region(self, region_label: str) -> None:
        """Nome della regione scelta in Impostazioni (quella mostrata nel footer), da
        indicare accanto ai timer: sono calcolati per quella regione, non per tutte."""
        self._timers_hint.setText(tr("bdo.timers_hint", region=region_label))

    def _set_value(self, region: str, text: str, color: str) -> None:
        label = self._value_labels[region]
        label.setText(f"<b>{text}</b>")
        label.setStyleSheet(f"color: {color};")

    def show_status(self, statuses: dict[str, RegionStatus]) -> None:
        self._message.setText("")
        for region in REGIONS:
            text, color = describe_region(statuses.get(region))
            self._set_value(region, text, color)

    def set_estimate_controls(self, visible: bool, text: str = "", can_finish: bool = False) -> None:
        """Pulsanti "+1 ora" / "È già finita" (con una domanda sopra, se text c'è); visible False li nasconde."""
        self._estimate_box.setVisible(visible)
        if visible:
            self._estimate_label.setText(text)
            self._estimate_label.setVisible(bool(text))
            self._finished_btn.setVisible(can_finish)

    def show_error(self, kind: str) -> None:
        """Errore (o chiave mancante): le regioni tornano "n/d" e sotto compare il motivo."""
        for region in REGIONS:
            self._set_value(region, tr("server.unknown"), COLOR_UNKNOWN)
        self._message.setText(describe_error(kind)[0])

    def show_news(self, items: list[NewsItem], upcoming: NewsItem | None) -> None:
        """upcoming: l'annuncio da mettere in evidenza (lo sceglie MainWindow: vedi pick_current)."""
        if upcoming is not None:
            when = upcoming.maintenance_date.strftime("%d-%m-%Y")
            key = "bdo.news_upcoming_temp" if upcoming.is_temporary else "bdo.news_upcoming"
            self._upcoming.setText(f"<b>{html.escape(tr(key, date=when))}</b>")
            self._upcoming.setStyleSheet(f"color: {announced_color(upcoming.is_temporary)};")
        else:
            self._upcoming.setText(tr("bdo.news_none_upcoming"))
            self._upcoming.setStyleSheet("")
        lines = []
        for item in items:
            title = html.escape(item.title)
            if item.url:
                title = f'<a href="{html.escape(item.url, quote=True)}">{title}</a>'
            if item.is_maintenance and item.affects_servers:  # solo quelle che fermano il gioco in rosso
                title = f'<b style="color: {COLOR_MAINTENANCE};">{title}</b>'
            posted = item.posted.strftime("%d-%m-%Y") if item.posted else ""
            lines.append(f"{posted} &nbsp; {title}")
        self._news_list.setText("<br>".join(lines))

    def set_maintenance_info(self, title: str | None, color: str, reason: str, source_tip: str) -> None:
        """Titolo con la fascia oraria (a colori) e il motivo sotto, una frase per riga; title None nasconde
        tutto il blocco. source_tip: da dove viene l'orario, mostrato passando il mouse sul titolo."""
        self._info_box.setVisible(bool(title))
        if not title:
            return
        self._info_title.setText(title)
        self._info_title.setStyleSheet(f"color: {color};")
        self._info_title.setToolTip(source_tip)
        has_reason = bool(reason)
        self._reason_caption.setVisible(has_reason)
        self._reason_frame.setVisible(has_reason)
        if has_reason:
            # Barra colorata a sinistra e fondo appena tinto: il motivo si stacca dal resto.
            self._reason_frame.setStyleSheet(
                f"#reasonFrame {{ border-left: 3px solid {color}; background: rgba(127, 127, 127, 0.10); border-radius: 3px; }}"
            )
            self._reason.setText("\n".join(line for line in reason.split("\n") if line))

    def show_patch_notes(self, items: list[NewsItem]) -> None:
        """Le ultime patch notes: titolo, data e link al sito (il contenuto non si riassume: è lungo e cambia formato)."""
        lines = []
        for item in items:
            title = html.escape(item.title)
            if item.url:
                title = f'<a href="{html.escape(item.url, quote=True)}">{title}</a>'
            posted = item.posted.strftime("%d-%m-%Y") if item.posted else ""
            lines.append(f"{posted} &nbsp; {title}")
        self._patch_list.setText("<br>".join(lines) if lines else html.escape(tr("bdo.patch_none")))

    def show_patch_error(self, kind: str) -> None:
        self._patch_list.setText(html.escape(describe_error(kind)[0]))

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

    # -- Confronto con la gilda in gioco --------------------------------------
    def show_guild_message(self, text: str) -> None:
        self._guild_label.setText(html.escape(text))

    def show_guild(self, info: GuildInfo, comparison: GuildComparison, status_names: dict[str, str]) -> None:
        lines = [f"<b>{html.escape(tr('bdo.guild_summary', name=info.name, count=len(info.members), master=info.master))}</b>"]
        groups = [
            ("bdo.guild_not_in_app", [html.escape(n) for n in comparison.not_in_app]),
            (
                "bdo.guild_ex_banned",
                [f"{html.escape(n)} ({html.escape(status_names.get(s, s))})" for n, s in comparison.ex_or_banned_in_game],
            ),
            ("bdo.guild_not_in_game", [html.escape(n) for n in comparison.active_not_in_game]),
        ]
        any_diff = False
        for key, names in groups:
            if not names:
                continue
            any_diff = True
            shown = ", ".join(names[:GUILD_NAMES_SHOWN])
            more = len(names) - GUILD_NAMES_SHOWN
            suffix = f" … +{more}" if more > 0 else ""
            lines.append(f"{html.escape(tr(key, n=len(names)))} {shown}{suffix}")
        if not any_diff:
            lines.append(html.escape(tr("bdo.guild_all_match")))
        self._guild_label.setText("<br>".join(lines))
