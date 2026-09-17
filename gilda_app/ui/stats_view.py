from PySide6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget
from qfluentwidgets import CardWidget, StrongBodyLabel, SubtitleLabel

from gilda_app.db import stats
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO


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
        layout.addWidget(QLabel("Nessun dato disponibile.", card))
    for line in lines:
        layout.addWidget(QLabel(line, card))
    return card


class StatsPage(QScrollArea):
    """Dashboard statistiche sull'elenco membri."""

    def __init__(self, get_conn, parent=None):
        super().__init__(parent)
        self.get_conn = get_conn
        self.setWidgetResizable(True)

        self.content = QWidget()
        self.setWidget(self.content)
        self.main_layout = QVBoxLayout(self.content)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)
        self.main_layout.addWidget(SubtitleLabel("Statistiche", self.content))

        self.refresh()

    def refresh(self) -> None:
        while self.main_layout.count() > 1:
            item = self.main_layout.takeAt(1)
            self._clear_item(item)

        conn = self.get_conn()

        counts = stats.counts_by_status(conn)
        cards_layout = QGridLayout()
        cards_layout.addWidget(_stat_card("Membri attuali", str(counts[STATUS_ATTIVO])), 0, 0)
        cards_layout.addWidget(_stat_card("Ex membri", str(counts[STATUS_EX_MEMBRO])), 0, 1)
        cards_layout.addWidget(_stat_card("Bannati", str(counts[STATUS_BANNATO])), 0, 2)
        cards_layout.addWidget(_stat_card("Totale storico", str(counts["totale_storico"])), 0, 3)
        self.main_layout.addLayout(cards_layout)

        avg_tenure = stats.avg_tenure_days(conn)
        tenure_text = f"{avg_tenure:.0f} giorni" if avg_tenure is not None else "n/d"
        rate = stats.rejoin_rate(conn)
        recent = stats.recent_changes(conn, days=30)

        cards_layout2 = QGridLayout()
        cards_layout2.addWidget(_stat_card("Permanenza media prima di uscire", tenure_text), 0, 0)
        cards_layout2.addWidget(_stat_card("Tasso di rientro", f"{rate:.1f}%"), 0, 1)
        cards_layout2.addWidget(
            _stat_card("Movimenti ultimi 30 giorni", f"+{recent.get(STATUS_ATTIVO, 0)} / -{recent.get(STATUS_EX_MEMBRO, 0) + recent.get(STATUS_BANNATO, 0)}"),
            0,
            2,
        )
        self.main_layout.addLayout(cards_layout2)

        self.main_layout.addWidget(self._trend_chart_card(conn))
        self.main_layout.addWidget(self._nation_chart_card(conn))

        top_rejoiners = stats.top_rejoiners(conn)
        self.main_layout.addWidget(
            _list_card(
                "Membri con più rientri",
                [f"{r['family_name']} ({r['main_name']}) — {r['rejoin_count']} rientri" for r in top_rejoiners],
            )
        )

        ban_reasons = stats.common_ban_reasons(conn)
        self.main_layout.addWidget(
            _list_card(
                "Motivi di ban più comuni",
                [f"{r['note']} — {r['cnt']} casi" for r in ban_reasons],
            )
        )

        hall_of_fame = stats.hall_of_fame(conn)
        self.main_layout.addWidget(
            _list_card(
                "Hall of fame (membri attuali più anziani)",
                [f"{r['family_name']} ({r['main_name']}) — dal {r['since'][:10]}" for r in hall_of_fame],
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
        layout.addWidget(StrongBodyLabel("Andamento membri attivi nel tempo", card))

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

        axis_y = QValueAxis()
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
        layout.addWidget(StrongBodyLabel("Distribuzione per nazione (membri attuali, top 10)", card))

        rows = stats.nation_distribution(conn, STATUS_ATTIVO)[:10]
        bar_set = QBarSet("Membri")
        categories = []
        for row in rows:
            bar_set.append(row["cnt"])
            categories.append(row["nation"])

        series = QBarSeries()
        series.append(bar_set)

        chart = QChart()
        chart.addSeries(series)
        chart.legend().hide()
        chart.setBackgroundVisible(False)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories or ["-"])
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setMinimumHeight(280)
        layout.addWidget(view)
        return card
