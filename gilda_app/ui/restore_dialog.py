from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidgetItem
from qfluentwidgets import ListWidget, MessageBoxBase, SubtitleLabel

from gilda_app.db.backup import BackupInfo
from gilda_app.i18n import tr

_KNOWN_REASONS = {"auto", "manual", "move", "import", "reset", "pre-restore"}


def reason_label(reason: str) -> str:
    return tr(f"backup.reason.{reason}") if reason in _KNOWN_REASONS else reason


def format_backup_when(info: BackupInfo) -> str:
    return info.created.strftime("%d-%m-%Y %H:%M")


class RestoreBackupDialog(MessageBoxBase):
    """Elenco dei backup disponibili, dal più recente; ritorna quello scelto."""

    def __init__(self, parent, backups: list[BackupInfo]):
        super().__init__(parent)
        self._backups = backups
        self.viewLayout.addWidget(SubtitleLabel(tr("backup.restore.title"), self))
        hint = QLabel(tr("backup.restore.hint"), self)
        hint.setWordWrap(True)
        self.viewLayout.addWidget(hint)

        self.list_widget = ListWidget(self)
        self.list_widget.setMinimumHeight(220)
        for info in backups:
            size_kb = max(1, info.size // 1024)
            item = QListWidgetItem(f"{format_backup_when(info)}  -  {reason_label(info.reason)}  ({size_kb} KB)")
            item.setData(Qt.UserRole, str(info.path))
            self.list_widget.addItem(item)
        if backups:
            self.list_widget.setCurrentRow(0)
        else:
            empty = QListWidgetItem(tr("backup.restore.empty"))
            empty.setFlags(Qt.NoItemFlags)
            self.list_widget.addItem(empty)
        self.list_widget.itemDoubleClicked.connect(lambda _item: self.yesButton.click())
        self.viewLayout.addWidget(self.list_widget)

        self.widget.setMinimumWidth(520)
        self.yesButton.setText(tr("backup.restore.button"))
        self.cancelButton.setText(tr("button.cancel"))
        self.yesButton.setEnabled(bool(backups))

    def selected_backup(self) -> BackupInfo | None:
        row = self.list_widget.currentRow()
        if not self._backups or row < 0 or row >= len(self._backups):
            return None
        return self._backups[row]
