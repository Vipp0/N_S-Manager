from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout
from qfluentwidgets import ProgressBar


class ImportProgressDialog(QDialog):
    """Popup non interattivo con barra di avanzamento, mostrato durante l'import."""

    def __init__(self, parent=None, title: str = "Importazione in corso..."):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(360, 110)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.label = QLabel("Preparazione...", self)
        layout.addWidget(self.label)

        self.bar = ProgressBar(self)
        self.bar.setRange(0, 100)
        layout.addWidget(self.bar)

    def set_progress(self, current: int, total: int) -> None:
        percent = int(current / total * 100) if total else 100
        self.bar.setValue(percent)
        self.label.setText(f"Importazione in corso... {current}/{total} righe")
