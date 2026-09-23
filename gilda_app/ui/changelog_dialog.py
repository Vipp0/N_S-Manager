from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import MessageBoxBase, ScrollArea, StrongBodyLabel, SubtitleLabel

from gilda_app.changelog import CHANGELOG
from gilda_app.i18n import tr


class ChangelogDialog(MessageBoxBase):
    """Elenco di sola lettura delle versioni rilasciate, più recente in cima."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.viewLayout.addWidget(SubtitleLabel(tr("settings.changelog"), self))

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 12, 0)
        content_layout.setSpacing(14)
        for entry in CHANGELOG:
            content_layout.addWidget(self._version_block(entry, content))
        content_layout.addStretch(1)

        scroll = ScrollArea(self)
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.enableTransparentBackground()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMinimumHeight(360)
        self.viewLayout.addWidget(scroll)

        self.widget.setMinimumWidth(560)
        self.yesButton.setText(tr("button.close"))
        self.cancelButton.hide()

    @staticmethod
    def _version_block(entry: dict, parent: QWidget) -> QWidget:
        block = QWidget(parent)
        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(StrongBodyLabel(f"{entry['version']} — {entry['date']}", block))
        for note in entry["notes"]:
            label = QLabel(f"•  {note}", block)
            label.setWordWrap(True)
            layout.addWidget(label)
        return block
