from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import CardWidget, FluentIcon as FIF, PrimaryPushButton, PushButton, SubtitleLabel


class SettingsPage(QWidget):
    import_requested = Signal()
    export_requested = Signal()
    reset_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        layout.addWidget(SubtitleLabel("Impostazioni", self))

        import_card = CardWidget(self)
        import_layout = QVBoxLayout(import_card)
        import_btn = PrimaryPushButton(FIF.DOWNLOAD, "Importa da Excel...", import_card)
        import_btn.clicked.connect(self.import_requested)
        import_layout.addWidget(import_btn)
        layout.addWidget(import_card)

        export_card = CardWidget(self)
        export_layout = QVBoxLayout(export_card)
        export_btn = PushButton(FIF.SAVE, "Esporta in Excel...", export_card)
        export_btn.clicked.connect(self.export_requested)
        export_layout.addWidget(export_btn)
        layout.addWidget(export_card)

        reset_card = CardWidget(self)
        reset_layout = QVBoxLayout(reset_card)
        reset_btn = PushButton(FIF.DELETE, "Azzera database", reset_card)
        reset_btn.setStyleSheet("color: #c42b1c;")
        reset_btn.clicked.connect(self.reset_requested)
        reset_layout.addWidget(reset_btn)
        layout.addWidget(reset_card)

        layout.addStretch(1)
