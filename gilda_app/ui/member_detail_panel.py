"""Il pannello dei dettagli a destra nelle schermate Membri: i dati più importanti del membro scelto, a colpo
d'occhio. Si apre con un clic su una riga (vedi member_table.py) e si chiude con la X. I dati li prepara
utils/member_summary.py; qui c'è solo il disegno."""
from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    FluentIcon as FIF,
    PrimaryPushButton,
    PushButton,
    ScrollArea,
    SubtitleLabel,
    ToolButton,
    isDarkTheme,
    themeColor,
)

from gilda_app.i18n import tr
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO, Member
from gilda_app.ui.chips import (
    TONE_ACCENT,
    TONE_BAD,
    TONE_GOOD,
    TONE_NEUTRAL,
    TONE_OUTLINE,
    TONE_WARN,
    ChipLabel,
    chip_foreground,
)
from gilda_app.utils.flags import flag_pixmap, nations_text
from gilda_app.utils.member_summary import TAG_NEW, MemberSummary

PANEL_WIDTH = 340
HISTORY_SHOWN = 2  # i passaggi visibili; gli altri dietro "Mostra altro"
FLAG_HEIGHT = 19
STATUS_CHIP_TONES = {STATUS_ATTIVO: TONE_GOOD, STATUS_EX_MEMBRO: TONE_WARN, STATUS_BANNATO: TONE_BAD}
HISTORY_TONES = {"good": TONE_GOOD, "bad": TONE_BAD, "neutral": TONE_NEUTRAL}
COPIED_MS = 1600


def _faint() -> QColor:
    return QColor(255, 255, 255, 140) if isDarkTheme() else QColor(0, 0, 0, 125)


def _line() -> QColor:
    return QColor(255, 255, 255, 28) if isDarkTheme() else QColor(0, 0, 0, 22)


class _PanelCard(CardWidget):
    """Lo sfondo del pannello: come un riquadro ma fermo (nessun effetto al passaggio del mouse), con una sfumatura
    nel colore d'accento sulla striscia in alto."""

    HEADER_HEIGHT = 50

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.ArrowCursor)

    def _hoverBackgroundColor(self):
        return self._normalBackgroundColor()

    def _pressedBackgroundColor(self):
        return self._normalBackgroundColor()

    def paintEvent(self, event) -> None:
        # Sfondo pieno sotto quello del riquadro (che è un po' trasparente): quando il pannello copre la tabella
        # le righe sotto non devono vedersi attraverso.
        solid = QPainter(self)
        solid.setRenderHint(QPainter.Antialiasing)
        solid.setPen(Qt.NoPen)
        solid.setBrush(QColor(43, 43, 43) if isDarkTheme() else QColor(255, 255, 255))
        solid.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), self.borderRadius, self.borderRadius)
        solid.end()
        CardWidget.paintEvent(self, event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(self.rect().adjusted(1, 1, -1, -1), self.borderRadius, self.borderRadius)
        painter.setClipPath(clip)
        tint = QColor(themeColor())
        tint.setAlpha(46 if isDarkTheme() else 34)
        gradient = QLinearGradient(0, 0, self.width() * 0.75, 0)
        gradient.setColorAt(0, tint)
        tint.setAlpha(0)
        gradient.setColorAt(1, tint)
        painter.fillRect(0, 0, self.width(), self.HEADER_HEIGHT, gradient)
        painter.setPen(QPen(_line(), 1))
        painter.drawLine(0, self.HEADER_HEIGHT, self.width(), self.HEADER_HEIGHT)


class _Dot(QLabel):
    """Il pallino colorato davanti a un passaggio dello storico."""

    def __init__(self, tone: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(8, 8)
        color = chip_foreground(tone)
        self.setStyleSheet(f"background: {color.name()}; border-radius: 4px;")


class MemberDetailPanel(QWidget):
    close_requested = Signal()
    edit_requested = Signal(object)
    move_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(PANEL_WIDTH)
        self.member: Member | None = None
        self._summary: MemberSummary | None = None
        self._history_all = False
        self._copied = False
        self._copy_timer = QTimer(self)
        self._copy_timer.setSingleShot(True)
        self._copy_timer.timeout.connect(self._copy_done)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._card = _PanelCard(self)
        outer.addWidget(self._card)
        card = QVBoxLayout(self._card)
        card.setContentsMargins(0, 0, 0, 0)
        card.setSpacing(0)

        # striscia in alto: lo stato e la X
        head = QHBoxLayout()
        head.setContentsMargins(16, 0, 8, 0)
        self._status_holder = QHBoxLayout()
        head.addLayout(self._status_holder)
        head.addStretch(1)
        close = ToolButton(FIF.CLOSE, self._card)
        close.setToolTip(tr("panel.close"))
        close.setFixedSize(30, 30)
        close.clicked.connect(self.close_requested)
        head.addWidget(close)
        header = QWidget(self._card)
        header.setFixedHeight(_PanelCard.HEADER_HEIGHT)
        header.setLayout(head)
        card.addWidget(header)

        # corpo scorrevole (nelle finestre basse la scheda può superare l'altezza)
        self._scroll = ScrollArea(self._card)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.enableTransparentBackground()
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._content = QWidget()
        self._content.setObjectName("detailContent")
        self._content.setStyleSheet("#detailContent { background: transparent; }")
        self._body = QVBoxLayout(self._content)
        self._body.setContentsMargins(18, 16, 18, 8)
        self._body.setSpacing(12)
        self._scroll.setWidget(self._content)
        card.addWidget(self._scroll, 1)

        # pulsanti in fondo
        feet = QHBoxLayout()
        feet.setContentsMargins(18, 10, 18, 16)
        feet.setSpacing(8)
        self._edit = PrimaryPushButton(tr("panel.edit"), self._card)
        self._edit.clicked.connect(lambda: self.member is not None and self.edit_requested.emit(self.member))
        self._move = PushButton(tr("panel.move"), self._card)
        self._move.clicked.connect(lambda: self.member is not None and self.move_requested.emit(self.member))
        feet.addWidget(self._edit, 1)
        feet.addWidget(self._move, 1)
        card.addLayout(feet)

    # -- contenuto ---------------------------------------------------------------------------------
    def set_member(self, member: Member, summary: MemberSummary) -> None:
        if self.member is None or self.member.id != member.id:
            self._history_all = False  # un altro membro: lo storico torna corto
            self._copied = False
        self.member, self._summary = member, summary
        self._rebuild()

    def _clear(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget, inner = item.widget(), item.layout()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif inner is not None:
                self._clear(inner)

    def _block(self, title: str, widget_or_layout, with_line: bool = True) -> None:
        """Un blocco con il titolo piccolo in maiuscolo e una linea sopra (tranne il primo)."""
        if with_line:
            line = QFrame(self._content)
            line.setFixedHeight(1)
            line.setStyleSheet(f"background: rgba({_line().red()}, {_line().green()}, {_line().blue()}, {_line().alpha()}); border: none;")
            self._body.addWidget(line)
        caption = CaptionLabel(title.upper(), self._content)
        caption.setTextColor(_faint(), _faint())
        self._body.addWidget(caption)
        if hasattr(widget_or_layout, "addWidget"):  # un layout
            self._body.addLayout(widget_or_layout)
        else:
            self._body.addWidget(widget_or_layout)

    def _text(self, text: str, faint: bool = False) -> BodyLabel:
        label = BodyLabel(text, self._content)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        if faint:
            label.setTextColor(_faint(), _faint())
        return label

    def _rebuild(self) -> None:
        member, summary = self.member, self._summary
        self._clear(self._status_holder)
        self._clear(self._body)
        self._status_holder.addWidget(ChipLabel(tr(f"chip.status.{member.status}"), STATUS_CHIP_TONES[member.status]))

        # nome, main, nazione con la bandiera
        name_row = QHBoxLayout()
        name_row.setSpacing(10)
        name = SubtitleLabel(member.family_name, self._content)
        name.setWordWrap(True)
        name.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        name_row.addWidget(name, 0)
        if summary.tag:
            name_row.addWidget(ChipLabel(tr("chip.new") if summary.tag == TAG_NEW else tr("chip.rejoined"),
                                         TONE_ACCENT if summary.tag == TAG_NEW else TONE_OUTLINE), 0, Qt.AlignVCenter)
        name_row.addStretch(1)
        self._body.addLayout(name_row)
        if member.main_name:
            self._body.addWidget(self._text(tr("panel.main", name=member.main_name), faint=True))
        if member.nations:
            nations = QHBoxLayout()
            nations.setSpacing(8)
            flags = QHBoxLayout()
            flags.setSpacing(-4)
            for nation in member.nations:
                flag = QLabel(self._content)
                flag.setPixmap(flag_pixmap(nation).scaledToHeight(FLAG_HEIGHT, Qt.SmoothTransformation))
                flags.addWidget(flag)
            nations.addLayout(flags)
            nations.addWidget(self._text(nations_text(member.nations)), 1)
            self._body.addLayout(nations)

        # Discord con il pulsante Copia
        discord = QHBoxLayout()
        discord.addWidget(self._text(member.discord_name or "—"), 1)
        copy = PushButton(FIF.ACCEPT if self._copied else FIF.COPY, tr("panel.copied") if self._copied else tr("panel.copy"), self._content)
        copy.setFixedHeight(28)
        copy.setEnabled(bool(member.discord_name))
        copy.clicked.connect(self._copy_discord)
        discord.addWidget(copy)
        self._block(tr("panel.discord"), discord)

        # da quando è in gilda / quando è uscito / quando è stato bannato
        title = {STATUS_ATTIVO: "panel.in_guild", STATUS_EX_MEMBRO: "panel.left", STATUS_BANNATO: "panel.banned"}[member.status]
        when = QVBoxLayout()
        when.setSpacing(2)
        if summary.missing_join_date:
            when.addWidget(self._text(tr("panel.no_join_date"), faint=True))
            add = PushButton(tr("panel.add_date"), self._content)
            add.setFixedHeight(28)
            add.clicked.connect(lambda: self.edit_requested.emit(self.member))  # la data si inserisce nella modifica
            when.addWidget(add, 0, Qt.AlignLeft)
        else:
            when.addWidget(self._text(summary.in_guild))
            if summary.first_join:
                when.addWidget(self._text(summary.first_join, faint=True))
        self._block(tr(title), when)

        if member.status == STATUS_EX_MEMBRO:
            chip = ChipLabel(tr("panel.still_yes"), TONE_WARN) if member.still_on_discord else ChipLabel(tr("panel.still_no"), TONE_OUTLINE)
            holder = QHBoxLayout()
            holder.addWidget(chip, 0, Qt.AlignLeft)
            holder.addStretch(1)
            self._block(tr("panel.still_on_discord"), holder)
        if member.status == STATUS_BANNATO:
            reason = summary.ban_reason
            self._block(tr("panel.ban_reason"), self._text(reason or tr("panel.no_reason"), faint=not reason))

        # nota per intero (nella tabella è tagliata)
        self._block(tr("panel.note"), self._text(member.note or tr("panel.no_note"), faint=not member.note))

        # ultimi passaggi
        if len(summary.history) > 1 or (summary.history and summary.history[0].key != "joined"):
            shown = summary.history if self._history_all else summary.history[:HISTORY_SHOWN]
            history = QVBoxLayout()
            history.setSpacing(6)
            for item in shown:
                row = QHBoxLayout()
                row.setSpacing(10)
                row.addWidget(_Dot(HISTORY_TONES[item.tone], self._content), 0, Qt.AlignVCenter)
                label = BodyLabel(tr(f"chip.{item.key}"), self._content)
                if item.note:
                    label.setToolTip(item.note)
                row.addWidget(label, 1)
                day = CaptionLabel(item.day, self._content)
                day.setTextColor(_faint(), _faint())
                row.addWidget(day)
                history.addLayout(row)
            extra = len(summary.history) - HISTORY_SHOWN
            if extra > 0:
                more = PushButton(tr("panel.show_less") if self._history_all else tr("panel.show_more", n=extra), self._content)
                more.setFixedHeight(28)
                more.clicked.connect(self._toggle_history)
                history.addWidget(more, 0, Qt.AlignLeft)
            self._block(tr("panel.history"), history)
        self._body.addStretch(1)

    # -- azioni ------------------------------------------------------------------------------------
    def _toggle_history(self) -> None:
        self._history_all = not self._history_all
        self._rebuild()

    def _copy_discord(self) -> None:
        if self.member is None or not self.member.discord_name:
            return
        QGuiApplication.clipboard().setText(self.member.discord_name)
        self._copied = True
        self._rebuild()
        self._copy_timer.start(COPIED_MS)

    def _copy_done(self) -> None:
        self._copied = False
        if self.member is not None:
            self._rebuild()
