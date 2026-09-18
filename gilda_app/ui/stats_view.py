from PySide6.QtCharts import QAbstractBarSeries, QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication, QPainter
from PySide6.QtWidgets import QGridLayout, QLabel, QScrollArea, QToolTip, QVBoxLayout, QWidget
from qfluentwidgets import Action, CardWidget, FluentIcon as FIF, RoundMenu, StrongBodyLabel, SubtitleLabel

from gilda_app.db import stats
from gilda_app.db.database import get_members
from gilda_app.i18n import tr
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO, Member
from gilda_app.utils.flags import display_nation

# Numero minimo di membri con data di ingresso nota prima di mostrare la hall of fame,
# per non classificare come "più anziani" un gruppo di persone importate lo stesso giorno.
MIN_DATED_MEMBERS_FOR_HALL_OF_FAME = 3

# Tutte le nazioni insieme sarebbero troppe (una gilda tipica ne tocca 30-40, quasi
# tutte con 1-2 persone): mostriamo solo le più numerose, ma il mouseover/tasto destro
# su ogni barra dà comunque accesso a chi c'è in un gruppo, anche fuori dalla top N.
NATION_CHART_TOP_N = 15


def _stat_card(title: str, value: str) -> CardWidget:
    card = CardWidget()
    layout = QVBoxLayout(card)
    layout.addWidget(QLabel(title, card))
    value_label = StrongBodyLabel(value, card)
    value_label.setStyleSheet("font-size: 22px;")
    layout.addWidget(value_label)
    return card


def _list_card(title: str, lines: list[str]) -> CardWidget:
    card = CardWidget()
    layout = QVBoxLayout(card)
    layout.addWidget(StrongBodyLabel(title, card))
    if not lines:
        layout.addWidget(QLabel(tr("stats.no_data"), card))
    for line in lines:
        layout.addWidget(QLabel(line, card))
    return card


def _integer_value_axis(min_value: int, max_value: int) -> QValueAxis:
    """Asse dei valori con soli tick interi (niente ".0"/".5"): i nostri dati sono
    sempre conteggi di membri, mai frazionari. Forzare manualmente un numero di tick
    che non divide il range in passi interi (es. 11 tick su un range di 25) produceva
    passi come 2.5 e un'etichettatura instabile; applyNiceNumbers() lascia che Qt
    scelga passi interi "puliti" da solo."""
    axis = QValueAxis()
    axis.setLabelFormat("%d")
    if max_value <= min_value:
        max_value = min_value + 1
    axis.setRange(min_value, max_value)
    axis.applyNiceNumbers()
    # Per range piccoli applyNiceNumbers può comunque scegliere uno step frazionario
    # (es. 0-1 con 6 tick = passi da 0.2): forziamo un tick per unità in questo caso.
    span = axis.max() - axis.min()
    if span <= 10:
        axis.setTickCount(int(span) + 1)
    return axis


class StatsPage(QScrollArea):
    """Dashboard statistiche sull'elenco membri."""

    def __init__(self, get_conn, on_open_nation_filter=None, parent=None):
        super().__init__(parent)
        self.get_conn = get_conn
        self.on_open_nation_filter = on_open_nation_filter
        self.setWidgetResizable(True)

        # Stato del grafico nazioni per mouseover/tasto destro: ricostruito ad ogni
        # refresh() insieme al grafico stesso.
        self._nation_categories: list[str] = []
        self._nation_members: dict[str, list[Member]] = {}
        self._nation_hovered_index: int | None = None
        # Il tooltip sulle barre compare dopo un piccolo ritardo invece che all'istante,
        # così non lampeggia mentre si muove il mouse sul grafico.
        self._nation_tooltip_timer = QTimer(self)
        self._nation_tooltip_timer.setSingleShot(True)
        self._nation_tooltip_timer.setInterval(450)
        self._nation_tooltip_timer.timeout.connect(self._show_nation_tooltip)

        self.content = QWidget()
        self.setWidget(self.content)
        self.main_layout = QVBoxLayout(self.content)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)
        self.main_layout.addWidget(SubtitleLabel(tr("stats.title"), self.content))

        self.refresh()

    def refresh(self) -> None:
        while self.main_layout.count() > 1:
            item = self.main_layout.takeAt(1)
            self._clear_item(item)

        conn = self.get_conn()
        # Stessa condizione usata per la hall of fame: finché non ci sono abbastanza
        # membri con una data di ingresso realmente nota, anche le statistiche che
        # dipendono da dati "recenti" mostrerebbero solo il rumore del giorno
        # dell'import (tutti i movimenti registrati nello stesso istante).
        has_real_data = stats.dated_members_count(conn, STATUS_ATTIVO) >= MIN_DATED_MEMBERS_FOR_HALL_OF_FAME

        counts = stats.counts_by_status(conn)
        cards_layout = QGridLayout()
        cards_layout.addWidget(_stat_card(tr("stats.current_members"), str(counts[STATUS_ATTIVO])), 0, 0)
        cards_layout.addWidget(_stat_card(tr("stats.former_members"), str(counts[STATUS_EX_MEMBRO])), 0, 1)
        cards_layout.addWidget(_stat_card(tr("stats.banned"), str(counts[STATUS_BANNATO])), 0, 2)
        cards_layout.addWidget(_stat_card(tr("stats.total_history"), str(counts["totale_storico"])), 0, 3)
        self.main_layout.addLayout(cards_layout)

        avg_tenure = stats.avg_tenure_days(conn)
        tenure_text = tr("stats.avg_tenure_days", days=avg_tenure) if avg_tenure is not None else tr("stats.avg_tenure_unknown")
        rate = stats.rejoin_rate(conn)

        cards_layout2 = QGridLayout()
        cards_layout2.addWidget(_stat_card(tr("stats.avg_tenure"), tenure_text), 0, 0)
        cards_layout2.addWidget(_stat_card(tr("stats.rejoin_rate"), f"{rate:.1f}%"), 0, 1)
        if has_real_data:
            recent = stats.recent_changes(conn, days=30)
            cards_layout2.addWidget(
                _stat_card(
                    tr("stats.recent_changes"),
                    f"+{recent.get(STATUS_ATTIVO, 0)} / -{recent.get(STATUS_EX_MEMBRO, 0) + recent.get(STATUS_BANNATO, 0)}",
                ),
                0,
                2,
            )
        self.main_layout.addLayout(cards_layout2)

        self.main_layout.addWidget(self._trend_chart_card(conn))
        self.main_layout.addWidget(self._nation_chart_card(conn))

        top_rejoiners = stats.top_rejoiners(conn)
        self.main_layout.addWidget(
            _list_card(
                tr("stats.top_rejoiners"),
                [
                    tr("stats.top_rejoiners_line", name=r["family_name"], main=r["main_name"], count=r["rejoin_count"])
                    for r in top_rejoiners
                ],
            )
        )

        ban_reasons = stats.common_ban_reasons(conn)
        self.main_layout.addWidget(
            _list_card(
                tr("stats.ban_reasons"),
                [tr("stats.ban_reasons_line", reason=r["note"], count=r["cnt"]) for r in ban_reasons],
            )
        )

        # La hall of fame ha senso solo se un numero minimo di membri ha una data di
        # ingresso realmente nota: appena importato il database, tutti risultano
        # "iscritti" lo stesso giorno (quello dell'import), quindi la classifica
        # sarebbe priva di significato finché non si accumulano dati reali.
        if has_real_data:
            hall_of_fame = stats.hall_of_fame(conn)
            self.main_layout.addWidget(
                _list_card(
                    tr("stats.hall_of_fame"),
                    [
                        tr("stats.hall_of_fame_line", name=r["family_name"], main=r["main_name"], since=r["since"][:10])
                        for r in hall_of_fame
                    ],
                )
            )

        self.main_layout.addStretch(1)

    def _clear_item(self, item) -> None:
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
            return
        layout = item.layout()
        if layout is not None:
            while layout.count():
                self._clear_item(layout.takeAt(0))

    def _trend_chart_card(self, conn) -> CardWidget:
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.addWidget(StrongBodyLabel(tr("stats.trend_chart"), card))

        trend = stats.active_members_trend(conn)
        series = QLineSeries()
        for i, (month, value) in enumerate(trend):
            series.append(i, value)

        chart = QChart()
        chart.addSeries(series)
        chart.legend().hide()
        chart.setBackgroundVisible(False)

        axis_x = QBarCategoryAxis()
        axis_x.append([m for m, _ in trend] or ["-"])
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        values = [v for _, v in trend] or [0]
        axis_y = _integer_value_axis(min(0, min(values)), max(values))
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setMinimumHeight(280)
        layout.addWidget(view)
        return card

    def _nation_chart_card(self, conn) -> CardWidget:
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.addWidget(StrongBodyLabel(tr("stats.nation_chart"), card))
        layout.addWidget(QLabel(tr("stats.nation_chart_hint"), card))

        # Raggruppa per nome nazione risolto (non la stringa grezza nel DB: varianti/
        # alias come "Uk" e "United Kingdom" altrimenti apparirebbero come barre
        # separate), tenendo anche i membri di ciascun gruppo per mouseover/tasto
        # destro sulla barra.
        members_by_nation: dict[str, list[Member]] = {}
        for member in get_members(conn, STATUS_ATTIVO):
            for raw_nation in member.nations:
                name = display_nation(raw_nation)
                members_by_nation.setdefault(name, []).append(member)
        top_nations = sorted(members_by_nation.items(), key=lambda item: len(item[1]), reverse=True)[:NATION_CHART_TOP_N]

        self._nation_categories = [name for name, _ in top_nations]
        self._nation_members = dict(top_nations)
        self._nation_hovered_index = None

        bar_set = QBarSet(tr("stats.current_members"))
        for _, members in top_nations:
            bar_set.append(len(members))
        bar_set.hovered.connect(self._on_nation_bar_hovered)

        series = QBarSeries()
        series.append(bar_set)
        series.setLabelsVisible(True)
        series.setLabelsPosition(QAbstractBarSeries.LabelsInsideEnd)
        series.setLabelsFormat("@value")

        chart = QChart()
        chart.addSeries(series)
        chart.legend().hide()
        chart.setBackgroundVisible(False)

        axis_x = QBarCategoryAxis()
        axis_x.append(self._nation_categories or ["-"])
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        counts = [len(members) for _, members in top_nations] or [0]
        axis_y = _integer_value_axis(0, max(counts))
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setMinimumHeight(280)
        view.setMouseTracking(True)
        view.setContextMenuPolicy(Qt.CustomContextMenu)
        view.customContextMenuRequested.connect(lambda pos, v=view: self._on_nation_context_menu(v, pos))
        layout.addWidget(view)
        return card

    def _on_nation_bar_hovered(self, status: bool, index: int) -> None:
        self._nation_hovered_index = index if status else None
        if not status or index < 0 or index >= len(self._nation_categories):
            self._nation_tooltip_timer.stop()
            QToolTip.hideText()
            return
        # Riavvia il ritardo ad ogni cambio barra: il tooltip appare solo se il mouse
        # resta fermo su una barra, non mentre lo si trascina sul grafico.
        self._nation_tooltip_timer.start()

    def _show_nation_tooltip(self) -> None:
        index = self._nation_hovered_index
        if index is None or index < 0 or index >= len(self._nation_categories):
            return
        name = self._nation_categories[index]
        family_names = sorted(m.family_name for m in self._nation_members.get(name, []))
        QToolTip.showText(QCursor.pos(), "\n".join(family_names) or name)

    def _on_nation_context_menu(self, view: QChartView, pos) -> None:
        index = self._nation_hovered_index
        if index is None or index >= len(self._nation_categories):
            return
        name = self._nation_categories[index]
        members = self._nation_members.get(name, [])
        if not members:
            return

        menu = RoundMenu(parent=view)
        menu.addAction(
            Action(FIF.COPY, tr("stats.nation_menu.copy"), triggered=lambda: self._copy_nation_members(members))
        )
        if self.on_open_nation_filter is not None:
            menu.addAction(
                Action(
                    FIF.SEARCH,
                    tr("stats.nation_menu.open", nation=name),
                    triggered=lambda: self.on_open_nation_filter(name),
                )
            )
        menu.exec(view.viewport().mapToGlobal(pos))

    def _copy_nation_members(self, members: list[Member]) -> None:
        family_names = sorted(m.family_name for m in members)
        QGuiApplication.clipboard().setText("\n".join(family_names))
