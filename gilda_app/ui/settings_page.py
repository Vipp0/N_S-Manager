from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import CardWidget, ComboBox, FluentIcon as FIF, PrimaryPushButton, PushButton, StrongBodyLabel, SubtitleLabel

from gilda_app.i18n import LANGUAGES, get_language, tr


class SettingsPage(QWidget):
    import_requested = Signal()
    export_requested = Signal()
    reset_requested = Signal()
    language_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        layout.addWidget(SubtitleLabel(tr("settings.title"), self))

        language_card = CardWidget(self)
        language_layout = QVBoxLayout(language_card)
        language_layout.addWidget(StrongBodyLabel(tr("settings.language_label"), language_card))
        self.language_combo = ComboBox(language_card)
        self._lang_codes = list(LANGUAGES.keys())
        for code in self._lang_codes:
            self.language_combo.addItem(LANGUAGES[code], userData=code)
        self.language_combo.setCurrentIndex(self._lang_codes.index(get_language()))
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        language_layout.addWidget(self.language_combo)
        self.language_hint = StrongBodyLabel(tr("settings.language_hint"), language_card)
        self.language_hint.setStyleSheet("font-weight: normal; color: gray;")
        self.language_hint.hide()
        language_layout.addWidget(self.language_hint)
        layout.addWidget(language_card)

        import_card = CardWidget(self)
        import_layout = QVBoxLayout(import_card)
        import_btn = PrimaryPushButton(FIF.DOWNLOAD, tr("settings.import"), import_card)
        import_btn.clicked.connect(self.import_requested)
        import_layout.addWidget(import_btn)
        layout.addWidget(import_card)

        export_card = CardWidget(self)
        export_layout = QVBoxLayout(export_card)
        export_btn = PushButton(FIF.SAVE, tr("settings.export"), export_card)
        export_btn.clicked.connect(self.export_requested)
        export_layout.addWidget(export_btn)
        layout.addWidget(export_card)

        reset_card = CardWidget(self)
        reset_layout = QVBoxLayout(reset_card)
        reset_btn = PushButton(FIF.DELETE, tr("settings.reset"), reset_card)
        # Aggiunge il colore al QSS esistente di qfluentwidgets invece di sovrascriverlo:
        # setStyleSheet sostituisce l'intero stylesheet del pulsante (incluso il padding
        # riservato all'icona), causando la sovrapposizione icona/testo.
        reset_btn.setStyleSheet(reset_btn.styleSheet() + "\nPushButton { color: #c42b1c; }")
        reset_btn.clicked.connect(self.reset_requested)
        reset_layout.addWidget(reset_btn)
        layout.addWidget(reset_card)

        layout.addStretch(1)

    def _on_language_changed(self, index: int) -> None:
        code = self._lang_codes[index]
        self.language_hint.show()
        self.language_changed.emit(code)
