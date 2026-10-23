from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    FluentIcon as FIF,
    IconWidget,
    MessageBoxBase,
    ScrollArea,
    SimpleCardWidget,
    StrongBodyLabel,
    SubtitleLabel,
    TransparentPushButton,
)

from gilda_app.i18n import tr_in
from gilda_app.ui.changelog_dialog import ChangelogDialog
from gilda_app.whats_new import POPUP_LANGUAGE, WHATS_NEW, Highlight

ICON_SIZE = 30
MAX_HEIGHT = 380


class WhatsNewDialog(MessageBoxBase):
    """Popup "Novità della versione X": una scheda per ogni novità (icona, titolo, frase). Se le
    versioni sono più d'una (si è saltato un aggiornamento) ognuna ha la sua intestazione, la
    più recente in cima. `releases`: versioni di cui mostrare le novità, già in ordine."""

    def __init__(self, parent, releases: list[str]):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel(tr_in(POPUP_LANGUAGE, "whatsnew.title", version=releases[0]), self)
        self.viewLayout.addWidget(self.titleLabel)
        subtitle = CaptionLabel(tr_in(POPUP_LANGUAGE, "whatsnew.subtitle"), self)
        self.viewLayout.addWidget(subtitle)

        content = QWidget()
        content.setObjectName("whatsNewContent")
        content.setStyleSheet("#whatsNewContent { background: transparent; }")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 4, 12, 4)
        layout.setSpacing(10)
        for release in releases:
            if len(releases) > 1:
                layout.addWidget(StrongBodyLabel(tr_in(POPUP_LANGUAGE, "whatsnew.version_header", version=release), content))
            for highlight in WHATS_NEW[release]:
                layout.addWidget(self._card(highlight, content))
        layout.addStretch(1)

        self._scroll = ScrollArea(self)
        self._scroll.setWidget(content)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.enableTransparentBackground()
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._content = content
        self.viewLayout.addWidget(self._scroll)

        changelog_btn = TransparentPushButton(FIF.HISTORY, tr_in(POPUP_LANGUAGE, "whatsnew.changelog"), self)
        changelog_btn.clicked.connect(lambda: ChangelogDialog(self).exec())
        self.viewLayout.addWidget(changelog_btn, 0, Qt.AlignLeft)

        self.widget.setMinimumWidth(600)
        self.yesButton.setText(tr_in(POPUP_LANGUAGE, "whatsnew.close"))
        self.cancelButton.hide()

    @staticmethod
    def _card(highlight: Highlight, parent: QWidget) -> QWidget:
        card = SimpleCardWidget(parent)
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 14, 16, 14)
        row.setSpacing(14)
        icon = IconWidget(getattr(FIF, highlight.icon, FIF.INFO), card)
        icon.setFixedSize(ICON_SIZE, ICON_SIZE)
        row.addWidget(icon, 0, Qt.AlignTop)
        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        title, text = highlight.localized(POPUP_LANGUAGE)
        text_col.addWidget(StrongBodyLabel(title, card))
        body = BodyLabel(text, card)
        body.setWordWrap(True)
        text_col.addWidget(body)
        row.addLayout(text_col, 1)
        return card

    def _fit_scroll(self) -> None:
        """Altezza dell'elenco = quella del testo a capo alla larghezza vera, fino a un tetto
        oltre il quale scorre. Si misura dopo che il layout ha la larghezza definitiva."""
        width = self._scroll.viewport().width()
        needed = self._content.layout().heightForWidth(width) if width > 0 else self._content.sizeHint().height()
        self._scroll.setFixedHeight(min(max(needed, 80) + 8, MAX_HEIGHT))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._fit_scroll)
