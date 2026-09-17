from PySide6.QtCharts import QAbstractBarSeries, QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget
from qfluentwidgets import CardWidget, StrongBodyLabel, SubtitleLabel

from gilda_app.db import stats
from gilda_app.i18n import tr
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO
from gilda_app.utils.flags import display_nation

# Numero minimo di membri con data di ingresso nota prima di mostrare la hall of fame,
# per non classificare come "più anziani" un gruppo di persone importate lo stesso giorno.
MIN_DATED_MEMBERS_FOR_HALL_OF_FAME = 3


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

    def __init__(self, get_conn, parent=None):
        super().__init__(parent)
        self.get_conn = get_conn
        self.setWidgetResizable(True)

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

        # Il conteggio grezzo è per stringa esatta salvata nel DB: varianti/alias della
        # stessa nazione (es. "Uk" e "United Kingdom") altrimenti apparirebbero come
        # barre separate. Le riaggreghiamo per nome risolto prima di prendere il top 10.
        aggregated: dict[str, int] = {}
        for row in stats.nation_distribution(conn, STATUS_ATTIVO):
            name = display_nation(row["nation"])
            aggregated[name] = aggregated.get(name, 0) + row["cnt"]
        top_nations = sorted(aggregated.items(), key=lambda item: item[1], reverse=True)[:10]

        bar_set = QBarSet(tr("stats.current_members"))
        categories = []
        for name, cnt in top_nations:
            bar_set.append(cnt)
            categories.append(name)

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
        axis_x.append(categories or ["-"])
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        counts = [cnt for _, cnt in top_nations] or [0]
        axis_y = _integer_value_axis(0, max(counts))
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setMinimumHeight(280)
        layout.addWidget(view)
        return card
