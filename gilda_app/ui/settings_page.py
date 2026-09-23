from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    CaptionLabel,
    CardWidget,
    ComboBox,
    FluentIcon as FIF,
    PrimaryPushButton,
    PushButton,
    ScrollArea,
    StrongBodyLabel,
    SubtitleLabel,
)

from gilda_app.i18n import LANGUAGES, get_language, tr
from gilda_app.version import __version__


class SettingsPage(QWidget):
    import_requested = Signal()
    export_requested = Signal()
    reset_requested = Signal()
    language_changed = Signal(str)
    backup_now_requested = Signal()
    open_backups_requested = Signal()
    restore_requested = Signal()
    extra_dir_pick_requested = Signal()
    extra_dir_clear_requested = Signal()
    changelog_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Contenuto scorrevole: con la sezione Backup la pagina supera l'altezza di una
        # finestra piccola.
        content = QWidget()
        content.setObjectName("settingsContent")
        content.setStyleSheet("#settingsContent { background: transparent; }")
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

        backup_card = CardWidget(self)
        backup_layout = QVBoxLayout(backup_card)
        backup_layout.addWidget(StrongBodyLabel(tr("backup.title"), backup_card))
        backup_hint = QLabel(tr("backup.hint"), backup_card)
        backup_hint.setWordWrap(True)
        backup_layout.addWidget(backup_hint)
        backup_buttons = QHBoxLayout()
        create_btn = PrimaryPushButton(FIF.SAVE, tr("backup.create_now"), backup_card)
        create_btn.clicked.connect(self.backup_now_requested)
        open_btn = PushButton(FIF.FOLDER, tr("backup.open_folder"), backup_card)
        open_btn.clicked.connect(self.open_backups_requested)
        restore_btn = PushButton(FIF.HISTORY, tr("backup.restore"), backup_card)
        restore_btn.clicked.connect(self.restore_requested)
        for button in (create_btn, open_btn, restore_btn):
            backup_buttons.addWidget(button)
        backup_buttons.addStretch(1)
        backup_layout.addLayout(backup_buttons)

        backup_layout.addWidget(StrongBodyLabel(tr("backup.extra_label"), backup_card))
        self.extra_dir_label = QLabel(backup_card)
        self.extra_dir_label.setWordWrap(True)
        backup_layout.addWidget(self.extra_dir_label)
        extra_buttons = QHBoxLayout()
        extra_choose_btn = PushButton(FIF.FOLDER, tr("backup.extra_choose"), backup_card)
        extra_choose_btn.clicked.connect(self.extra_dir_pick_requested)
        self.extra_remove_btn = PushButton(tr("backup.extra_remove"), backup_card)
        self.extra_remove_btn.clicked.connect(self.extra_dir_clear_requested)
        extra_buttons.addWidget(extra_choose_btn)
        extra_buttons.addWidget(self.extra_remove_btn)
        extra_buttons.addStretch(1)
        backup_layout.addLayout(extra_buttons)
        layout.addWidget(backup_card)
        self.set_extra_backup_dir(None)

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
        changelog_btn = PushButton(FIF.HISTORY, tr("settings.changelog_button"), content)
        changelog_btn.clicked.connect(self.changelog_requested)
        layout.addWidget(changelog_btn)
        layout.addWidget(CaptionLabel(tr("settings.version", version=__version__), content))

    def set_extra_backup_dir(self, path: str | None) -> None:
        self.extra_dir_label.setText(path or tr("backup.extra_none"))
        self.extra_remove_btn.setEnabled(bool(path))

    def _on_language_changed(self, index: int) -> None:
        code = self._lang_codes[index]
        self.language_changed.emit(code)
