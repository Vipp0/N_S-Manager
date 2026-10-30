"""La copertina della dashboard: logo, numero dei membri con la barra dei posti, un grafico con tre viste
(ingressi e uscite, andamento, anzianità) e a lato ex membri e bannati. Ogni zona è cliccabile e porta alla
scheda giusta. Il disegno dei grafici è fatto a mano (QPainter): sono piccoli, non servono assi interattivi."""
import math
from datetime import date

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import SegmentedWidget, isDarkTheme, themeColor

from gilda_app.db.dashboard import TENURE_BUCKETS
from gilda_app.i18n import get_language, tr
from gilda_app.ui.chips import TONE_WARN, chip_foreground
from gilda_app.utils.date_format import iso_to_display

VIEW_TURNOVER, VIEW_TREND, VIEW_TENURE = "turn", "trend", "tenure"
VIEWS = (VIEW_TURNOVER, VIEW_TREND, VIEW_TENURE)
ZONE_ACTIVE, ZONE_EX, ZONE_BANNED, ZONE_CHART = "attivo", "ex_membro", "bannato", "stats"  # chiavi dei riquadri

MONTH_ABBR = {
    "it": ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}
COUNT_UP_MS = 900
FONT_FAMILY = "'Segoe UI', 'Microsoft YaHei', 'PingFang SC', sans-serif"  # come i testi di qfluentwidgets
WIDE_MIN_WIDTH = 1000  # sotto questa larghezza della pagina il grafico va su una seconda fila


def month_abbr(month_key: str) -> str:
    names = MONTH_ABBR.get(get_language(), MONTH_ABBR["en"])
    return names[int(month_key[5:7]) - 1]


def _text_color() -> QColor:
    return QColor(255, 255, 255, 225) if isDarkTheme() else QColor(0, 0, 0, 215)


def _faint_color() -> QColor:
    return QColor(255, 255, 255, 140) if isDarkTheme() else QColor(0, 0, 0, 125)


def _line_color() -> QColor:
    return QColor(255, 255, 255, 28) if isDarkTheme() else QColor(0, 0, 0, 22)


def _css(color: QColor) -> str:
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"


class ClickZone(QWidget):
    """Una zona della copertina che si illumina al passaggio del mouse e porta alla sua scheda con un clic."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover = False
        self.setCursor(Qt.PointingHandCursor)

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        if self._hover:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            tint = QColor(themeColor())
            tint.setAlpha(38 if isDarkTheme() else 30)
            painter.setPen(Qt.NoPen)
            painter.setBrush(tint)
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 9, 9)


class CapBar(QWidget):
    """La barra dei posti: piena in proporzione ai membri; oltre il tetto resta piena e diventa ambra."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._count, self._cap = 0, 100
        self.setFixedHeight(6)
        self.setMaximumWidth(240)

    def set_values(self, count: int, cap: int) -> None:
        self._count, self._cap = count, max(1, cap)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(_line_color())
        radius = self.height() / 2
        painter.drawRoundedRect(QRectF(self.rect()), radius, radius)
        painter.setBrush(chip_foreground(TONE_WARN) if self._count > self._cap else QColor(themeColor()))
        fraction = min(1.0, self._count / self._cap)
        painter.drawRoundedRect(QRectF(0, 0, max(self.height(), self.width() * fraction), self.height()), radius, radius)


class CoverChart(QWidget):
    """Il grafico della copertina, nella vista scelta. Disegna da solo, senza assi interattivi."""

    LEFT, RIGHT, TOP, BOTTOM = 8, 34, 12, 22

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(170)
        self._view = VIEW_TURNOVER
        self._turnover: list[dict] = []
        self._trend: list[tuple[str, int | None]] = []
        self._tenure: dict[str, int] = {}
        self._cap = 100

    def set_data(self, turnover, trend, tenure, cap) -> None:
        self._turnover, self._trend, self._tenure, self._cap = turnover, trend, tenure, cap
        self.update()

    def set_view(self, view: str) -> None:
        self._view = view
        self.update()

    def _plot(self) -> QRectF:
        return QRectF(self.LEFT, self.TOP, self.width() - self.LEFT - self.RIGHT, self.height() - self.TOP - self.BOTTOM)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        font = QFont("Segoe UI")
        font.setPixelSize(12)
        painter.setFont(font)
        {VIEW_TURNOVER: self._paint_turnover, VIEW_TREND: self._paint_trend, VIEW_TENURE: self._paint_tenure}[
            self._view
        ](painter)

    # -- ingressi e uscite --------------------------------------------------------------------------
    def _paint_turnover(self, painter: QPainter) -> None:
        plot = self._plot()
        if not self._turnover:
            return self._paint_empty(painter)
        values = [e["joins"] for e in self._turnover] + [e["exits"] for e in self._turnover if e["exits"] is not None]
        top = max(4, int(math.ceil(max(values + [1]) / 2) * 2))
        for step in (top / 2, top):
            y = plot.bottom() - plot.height() * step / top
            painter.setPen(QPen(_line_color(), 1))
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right() + 4, y))
            painter.setPen(_faint_color())
            painter.drawText(QRectF(plot.right() + 8, y - 8, self.RIGHT - 8, 16), Qt.AlignLeft | Qt.AlignVCenter, str(int(step)))
        group = plot.width() / len(self._turnover)
        bar = min(12.0, group * 0.32)
        accent = QColor(themeColor())
        gray = QColor(128, 128, 140, 150)
        painter.setPen(Qt.NoPen)
        for index, entry in enumerate(self._turnover):
            center = plot.left() + group * (index + 0.5)
            for offset, value, color in ((-bar - 1, entry["joins"], accent), (1, entry["exits"], gray)):
                if value is None:  # uscite non registrate in quel mese: niente barra, non uno zero
                    continue
                height = max(1.5, plot.height() * value / top) if value else 0
                painter.setBrush(color)
                painter.drawRoundedRect(QRectF(center + offset, plot.bottom() - height, bar, height), 2, 2)
            painter.setPen(_faint_color())
            painter.drawText(
                QRectF(center - group / 2, plot.bottom() + 4, group, self.BOTTOM - 4), Qt.AlignHCenter | Qt.AlignTop,
                month_abbr(entry["month"]),
            )
            painter.setPen(Qt.NoPen)

    # -- andamento ---------------------------------------------------------------------------------
    def _paint_trend(self, painter: QPainter) -> None:
        plot = self._plot()
        points = [(i, v) for i, (_month, v) in enumerate(self._trend) if v is not None]
        if len(points) < 2:
            return self._paint_empty(painter)
        values = [v for _i, v in points]
        show_cap = min(values) <= self._cap <= max(values) + 20
        low, high = min(values + ([self._cap] if show_cap else [])), max(values + ([self._cap] if show_cap else []))
        pad = max(2.0, (high - low) * 0.12)
        low, high = max(0.0, low - pad), high + pad
        count = len(self._trend)

        def x(index: int) -> float:
            return plot.left() + plot.width() * index / max(1, count - 1)

        def y(value: float) -> float:
            return plot.top() + plot.height() * (1 - (value - low) / (high - low))

        painter.setPen(QPen(_line_color(), 1))
        for k in (1, 2, 3):
            level = low + (high - low) * k / 4
            painter.drawLine(QPointF(plot.left(), y(level)), QPointF(plot.right() + 4, y(level)))
            painter.setPen(_faint_color())
            painter.drawText(QRectF(plot.right() + 8, y(level) - 8, self.RIGHT - 8, 16), Qt.AlignLeft | Qt.AlignVCenter, str(round(level)))
            painter.setPen(QPen(_line_color(), 1))
        if show_cap:
            dash = QPen(_faint_color(), 1, Qt.DashLine)
            painter.setPen(dash)
            painter.drawLine(QPointF(plot.left(), y(self._cap)), QPointF(plot.right() + 4, y(self._cap)))
            painter.drawText(QRectF(plot.left() + 2, y(self._cap) - 17, 80, 16), Qt.AlignLeft | Qt.AlignVCenter, f"{tr('dash.chart.cap')} {self._cap}")
        accent = QColor(themeColor())
        path = QPainterPath(QPointF(x(points[0][0]), y(points[0][1])))
        for index, value in points[1:]:
            path.lineTo(QPointF(x(index), y(value)))
        area = QPainterPath(path)
        area.lineTo(QPointF(x(points[-1][0]), plot.bottom()))
        area.lineTo(QPointF(x(points[0][0]), plot.bottom()))
        area.closeSubpath()
        gradient = QLinearGradient(0, plot.top(), 0, plot.bottom())
        top_color = QColor(accent)
        top_color.setAlpha(70)
        bottom_color = QColor(accent)
        bottom_color.setAlpha(0)
        gradient.setColorAt(0, top_color)
        gradient.setColorAt(1, bottom_color)
        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawPath(area)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(accent, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)
        last_index, last_value = points[-1]
        painter.setBrush(self.palette().base())
        painter.drawEllipse(QPointF(x(last_index), y(last_value)), 4.5, 4.5)
        painter.setPen(_text_color())
        regular = painter.font()
        bold = QFont(regular)
        bold.setBold(True)
        painter.setFont(bold)
        painter.drawText(QRectF(x(last_index) - 60, y(last_value) + 8, 52, 16), Qt.AlignRight | Qt.AlignVCenter, str(last_value))
        painter.setFont(regular)
        painter.setPen(_faint_color())
        for index in sorted({0, count // 4, count // 2, (3 * count) // 4, count - 1}):
            # la prima etichetta parte dal bordo sinistro e l'ultima finisce a destra, per non uscire dal grafico
            left = x(index) - 30 if 0 < index < count - 1 else (x(index) if index == 0 else x(index) - 60)
            align = Qt.AlignHCenter if 0 < index < count - 1 else (Qt.AlignLeft if index == 0 else Qt.AlignRight)
            painter.drawText(
                QRectF(left, plot.bottom() + 4, 60, self.BOTTOM - 4), align | Qt.AlignTop,
                month_abbr(self._trend[index][0]),
            )

    # -- anzianità ---------------------------------------------------------------------------------
    def _paint_tenure(self, painter: QPainter) -> None:
        rows = [(tr(f"dash.tenure.{key}"), self._tenure.get(key, 0)) for key in TENURE_BUCKETS]
        if self._tenure.get("nodate"):
            rows.append((tr("dash.tenure.nodate"), self._tenure["nodate"]))
        if not any(count for _label, count in rows):
            return self._paint_empty(painter)
        plot = QRectF(0, 2, self.width() - 4, self.height() - 4)
        row_height = min(28.0, plot.height() / len(rows))
        biggest = max(count for _label, count in rows)
        label_width, count_width = 116.0, 30.0
        accent = QColor(themeColor())
        accent.setAlpha(215)
        for index, (label, count) in enumerate(rows):
            top = plot.top() + row_height * index
            painter.setPen(_text_color())
            painter.drawText(QRectF(plot.left() + 2, top, label_width, row_height), Qt.AlignLeft | Qt.AlignVCenter, label)
            track = QRectF(plot.left() + label_width + 10, top + row_height / 2 - 4, plot.width() - label_width - count_width - 24, 8)
            painter.setPen(Qt.NoPen)
            painter.setBrush(_line_color())
            painter.drawRoundedRect(track, 4, 4)
            painter.setBrush(accent)
            painter.drawRoundedRect(QRectF(track.left(), track.top(), max(8.0, track.width() * count / biggest) if count else 0, 8), 4, 4)
            painter.setPen(_faint_color())
            painter.drawText(QRectF(plot.right() - count_width, top, count_width, row_height), Qt.AlignRight | Qt.AlignVCenter, str(count))

    def _paint_empty(self, painter: QPainter) -> None:
        painter.setPen(_faint_color())
        painter.drawText(QRectF(self.rect()), Qt.AlignCenter | Qt.TextWordWrap, tr("dash.chart.no_data"))


class CoverHero(QWidget):
    """La parte alta della copertina. Mostra i numeri e il grafico; l'aspetto (sfondo, bordo) lo dà la scheda."""

    zone_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._wide = None
        self._numbers = {ZONE_ACTIVE: 0, ZONE_EX: 0, ZONE_BANNED: 0}
        self._cap = 100
        self._animating = False
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(COUNT_UP_MS)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.valueChanged.connect(lambda value: self._render_numbers(float(value)))
        self._animation.finished.connect(self._finish_animation)

        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(0)

        # colonna di sinistra: logo, auguri di stagione, numero dei membri
        self.left = QWidget(self)
        left = QVBoxLayout(self.left)
        left.setContentsMargins(20, 16, 20, 16)
        left.setSpacing(2)
        left.addStretch(1)
        self.wordmark = QLabel(self.left)
        left.addWidget(self.wordmark, 0, Qt.AlignLeft)
        greeting_row = QHBoxLayout()
        greeting_row.setSpacing(6)
        self.greeting_icon = QLabel(self.left)
        self.greeting_icon.hide()
        greeting_row.addWidget(self.greeting_icon)
        self.greeting = QLabel(self.left)
        self.greeting.setStyleSheet(f"font-family: {FONT_FAMILY}; font-weight: 600; font-size: 15px;")
        self.greeting.hide()
        greeting_row.addWidget(self.greeting)
        greeting_row.addStretch(1)
        left.addLayout(greeting_row)
        left.addSpacing(6)
        self.active_zone = ClickZone(self.left)
        self.active_zone.clicked.connect(lambda: self.zone_clicked.emit(ZONE_ACTIVE))
        zone = QVBoxLayout(self.active_zone)
        zone.setContentsMargins(10, 6, 10, 8)
        zone.setSpacing(1)
        self._eyebrow = self._label("", 12, upper=True)
        zone.addWidget(self._eyebrow)
        self._big = self._label("", 56, weight=600)
        zone.addWidget(self._big)
        self._delta = self._label("", 14, accent=True, weight=600)
        zone.addWidget(self._delta)
        self._cap_bar = CapBar(self.active_zone)
        zone.addSpacing(4)
        zone.addWidget(self._cap_bar)
        self._slots = self._label("", 13)
        zone.addWidget(self._slots)
        left.addWidget(self.active_zone)
        left.addStretch(1)

        # colonna centrale: il grafico, con il selettore delle viste
        self.chart_zone = ClickZone(self)
        self.chart_zone.clicked.connect(lambda: self.zone_clicked.emit(ZONE_CHART))
        chart = QVBoxLayout(self.chart_zone)
        chart.setContentsMargins(16, 14, 16, 12)
        chart.setSpacing(6)
        head = QHBoxLayout()
        self._views = SegmentedWidget(self.chart_zone)
        for view in VIEWS:
            self._views.addItem(view, tr(f"dash.chart.view.{view}"), onClick=lambda _checked=False, v=view: self._set_view(v))
        self._views.setCurrentItem(VIEW_TURNOVER)
        head.addWidget(self._views, 0, Qt.AlignLeft)
        head.addStretch(1)
        self._legend = QLabel(self.chart_zone)
        self._legend.setTextFormat(Qt.RichText)
        self._legend.setAttribute(Qt.WA_TransparentForMouseEvents)
        head.addWidget(self._legend)
        chart.addLayout(head)
        self.chart = CoverChart(self.chart_zone)
        self.chart.setAttribute(Qt.WA_TransparentForMouseEvents)
        chart.addWidget(self.chart, 1)
        self._note = self._label("", 12)
        self._note.setWordWrap(True)
        chart.addWidget(self._note)

        # colonna di destra: ex membri e bannati
        self.right = QWidget(self)
        right = QVBoxLayout(self.right)
        right.setContentsMargins(14, 12, 14, 12)
        right.setSpacing(4)
        right.addStretch(1)
        self._mini = {}
        for key in (ZONE_EX, ZONE_BANNED):
            zone_widget = ClickZone(self.right)
            zone_widget.clicked.connect(lambda k=key: self.zone_clicked.emit(k))
            box = QVBoxLayout(zone_widget)
            box.setContentsMargins(10, 6, 10, 6)
            box.setSpacing(0)
            eyebrow = self._label("", 12, upper=True)
            number = self._label("", 26, weight=600)
            sub = self._label("", 13)
            for widget in (eyebrow, number, sub):
                box.addWidget(widget)
            right.addWidget(zone_widget)
            self._mini[key] = (eyebrow, number, sub)
        right.addStretch(1)

        self._view = VIEW_TURNOVER
        self._tracking_start: date | None = None
        self._tenure_total = 0
        self._turnover: list[dict] = []
        self._trend: list = []
        self.set_wide(True)

    def _label(self, text: str, size: int, weight: int = 400, upper: bool = False, accent: bool = False) -> QLabel:
        label = QLabel(text, self)
        label.setTextFormat(Qt.RichText)
        label.setAttribute(Qt.WA_TransparentForMouseEvents)  # il clic arriva alla zona sotto
        label.setProperty("fsize", size)
        label.setProperty("fweight", weight)
        label.setProperty("upper", upper)
        label.setProperty("accent", accent)
        self._style_label(label)
        return label

    @staticmethod
    def _style_label(label: QLabel, color: QColor | None = None) -> None:
        size, weight = label.property("fsize"), label.property("fweight")
        if color is None:
            color = QColor(themeColor()) if label.property("accent") else (_faint_color() if size <= 13 else _text_color())
        spacing = "letter-spacing: 1px;" if label.property("upper") else ""
        label.setStyleSheet(f"font-family: {FONT_FAMILY}; font-size: {size}px; font-weight: {weight}; color: {_css(color)}; {spacing}")

    # -- larghezza ---------------------------------------------------------------------------------
    def set_wide(self, wide: bool) -> None:
        """Larga: logo e numero | grafico | ex membri e bannati. Stretta: il grafico passa su una seconda fila."""
        if wide == self._wide:
            return
        self._wide = wide
        for widget in (self.left, self.chart_zone, self.right):
            self._grid.removeWidget(widget)
        if wide:
            self._grid.addWidget(self.left, 0, 0)
            self._grid.addWidget(self.chart_zone, 0, 1)
            self._grid.addWidget(self.right, 0, 2)
            for column, stretch in enumerate((11, 15, 8)):
                self._grid.setColumnStretch(column, stretch)
        else:
            self._grid.addWidget(self.left, 0, 0)
            self._grid.addWidget(self.right, 0, 1)
            self._grid.addWidget(self.chart_zone, 1, 0, 1, 2)
            for column, stretch in enumerate((1, 1, 0)):
                self._grid.setColumnStretch(column, stretch)
        self.left.setMinimumWidth(250)
        self.chart_zone.setMinimumWidth(300 if wide else 0)
        self.right.setMinimumWidth(190)
        self.update()

    def paintEvent(self, event) -> None:
        """Le linee tra le colonne (nella versione larga)."""
        if self._wide:
            painter = QPainter(self)
            painter.setPen(QPen(_line_color(), 1))
            for widget in (self.chart_zone, self.right):
                painter.drawLine(widget.x(), 12, widget.x(), self.height() - 12)

    # -- dati --------------------------------------------------------------------------------------
    def set_data(self, active: int, ex: int, banned: int, cap: int, joined_30: int, left_30: int, banned_30: int,
                 turnover: list, trend: list, tenure: dict, tracking_start: date | None) -> None:
        self._cap = cap
        self._numbers = {ZONE_ACTIVE: active, ZONE_EX: ex, ZONE_BANNED: banned}
        from gilda_app.models.member import STATUS_BANNATO, STATUS_EX_MEMBRO, STATUS_ATTIVO, status_label

        self._eyebrow.setText(status_label(STATUS_ATTIVO))
        self._delta.setText(tr("dash.joined_30", n=joined_30))
        over = active - cap
        self._cap_bar.set_values(active, cap)
        if over > 0:
            self._slots.setText(tr("dash.slots_over", n=over))
            self._style_label(self._slots, chip_foreground(TONE_WARN))
            self._slots.setStyleSheet(self._slots.styleSheet() + " font-weight: 600;")
        else:
            free = cap - active
            self._slots.setText(tr("dash.slots_free_one") if free == 1 else tr("dash.slots_free", n=free))
            self._style_label(self._slots)
        for key, status, recent_key, recent in (
            (ZONE_EX, STATUS_EX_MEMBRO, "dash.left_30", left_30),
            (ZONE_BANNED, STATUS_BANNATO, "dash.banned_30", banned_30),
        ):
            eyebrow, _number, sub = self._mini[key]
            eyebrow.setText(status_label(status))
            sub.setText(tr(recent_key, n=recent))
        self._tracking_start = tracking_start
        self._turnover, self._trend = turnover, trend
        self.chart.set_data(turnover, trend, tenure, cap)
        self._tenure_total = sum(tenure.values())
        self._update_legend_and_note()
        if not self._animating:
            self._render_numbers(1.0)

    def _render_numbers(self, progress: float) -> None:
        shown = {key: round(value * progress) for key, value in self._numbers.items()}
        faint = _css(_faint_color())
        self._big.setText(f'{shown[ZONE_ACTIVE]}<span style="font-size: 22px; font-weight: 500; color: {faint};"> / {self._cap}</span>')
        self._mini[ZONE_EX][1].setText(str(shown[ZONE_EX]))
        self._mini[ZONE_BANNED][1].setText(str(shown[ZONE_BANNED]))

    def play_count_up(self) -> None:
        """I numeri salgono da zero ai valori veri: una volta sola, all'avvio."""
        self._animating = True
        self._animation.start()

    def _finish_animation(self) -> None:
        self._animating = False
        self._render_numbers(1.0)

    # -- grafico: viste, legenda e nota ------------------------------------------------------------
    def _set_view(self, view: str) -> None:
        self._view = view
        self.chart.set_view(view)
        self._update_legend_and_note()

    def _update_legend_and_note(self) -> None:
        accent, faint = QColor(themeColor()).name(), _css(_faint_color())
        note = ""
        if self._view == VIEW_TURNOVER:
            joins = sum(e["joins"] for e in self._turnover)
            exits = sum(e["exits"] for e in self._turnover if e["exits"] is not None)
            legend = (
                f'<span style="color: {accent};">●</span> {tr("dash.chart.joins", n=joins)} &nbsp;&nbsp; '
                f'<span style="color: rgba(128,128,140,0.7);">●</span> {tr("dash.chart.exits", n=exits)}'
            )
            if self._tracking_start and any(e["exits"] is None for e in self._turnover):
                note = tr("dash.chart.note_exits", date=iso_to_display(self._tracking_start.isoformat()))
        elif self._view == VIEW_TREND:
            known = [(m, v) for m, v in self._trend if v is not None]
            legend = ""
            if len(known) >= 2:
                legend = tr("dash.chart.trend_delta", delta=f"{known[-1][1] - known[0][1]:+d}", since=month_abbr(known[0][0]))
            if self._tracking_start and any(v is None for _m, v in self._trend):
                note = tr("dash.chart.note_trend", date=iso_to_display(self._tracking_start.isoformat()))
        else:
            legend = tr("dash.chart.tenure_total", n=self._tenure_total)
        self._legend.setText(f'<span style="color: {faint}; font-size: 12px; font-family: {FONT_FAMILY};">{legend}</span>')
        self._note.setText(note)
        self._note.setVisible(bool(note))
