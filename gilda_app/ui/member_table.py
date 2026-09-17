from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QTableWidgetItem, QVBoxLayout, QWidget
from PySide6.QtGui import QGuiApplication
from qfluentwidgets import Action, FluentIcon as FIF
from qfluentwidgets import PrimaryPushButton, RoundMenu, SearchLineEdit, StrongBodyLabel, TableWidget

from gilda_app.models.member import STATUS_LABELS, Member
from gilda_app.utils.flags import combined_flag_icon, nations_text

COLUMNS = ["Family Name", "Main Name", "Nation", "Discord Name", "Note"]
NATION_COLUMN = 2


class MemberListPage(QWidget):
    """Tabella + ricerca per una singola lista (Attuali / Ex membri / Bannati)."""

    edit_requested = Signal(object)
    move_requested = Signal(object)
    delete_requested = Signal(object)
    add_requested = Signal(str)

    def __init__(self, status: str, parent=None):
        super().__init__(parent)
        self.status = status
        self._members: list[Member] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = StrongBodyLabel(STATUS_LABELS[status], self)
        self.search_box = SearchLineEdit(self)
        self.search_box.setPlaceholderText("Cerca per nome, nazione, discord...")
        self.search_box.setFixedWidth(320)
        self.search_box.textChanged.connect(self._apply_filter)
        add_btn = PrimaryPushButton(FIF.ADD, "Aggiungi membro", self)
        add_btn.clicked.connect(lambda: self.add_requested.emit(self.status))
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.search_box)
        header.addWidget(add_btn)
        layout.addLayout(header)

        self.table = TableWidget(self)
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

    def set_members(self, members: list[Member]) -> None:
        self._members = members
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(members))
        for row, member in enumerate(members):
            values = [
                member.family_name,
                member.main_name,
                nations_text(member.nations),
                member.discord_name,
                member.note or "",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, member.id)
                self.table.setItem(row, col, item)

            icon = combined_flag_icon(member.nations)
            if icon is not None:
                self.table.item(row, NATION_COLUMN).setIcon(icon)

        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        self._apply_filter(self.search_box.text())

    def _apply_filter(self, text: str) -> None:
        text = text.strip().lower()
        for row in range(self.table.rowCount()):
            if not text:
                self.table.setRowHidden(row, False)
                continue
            match = any(
                text in (self.table.item(row, col).text().lower())
                for col in range(self.table.columnCount())
                if self.table.item(row, col) is not None
            )
            self.table.setRowHidden(row, not match)

    def _member_at_row(self, row: int) -> Member | None:
        item = self.table.item(row, 0)
        if item is None:
            return None
        member_id = item.data(Qt.UserRole)
        return next((m for m in self._members if m.id == member_id), None)

    def _on_double_click(self, index) -> None:
        member = self._member_at_row(index.row())
        if member is not None:
            self.edit_requested.emit(member)

    def _show_context_menu(self, pos) -> None:
        row = self.table.rowAt(pos.y())
        col = self.table.columnAt(pos.x())
        if row < 0:
            return
        member = self._member_at_row(row)
        if member is None:
            return
        self.table.selectRow(row)

        menu = RoundMenu(parent=self.table)
        menu.addAction(Action(FIF.COPY, "Copia riga", triggered=lambda: self._copy_row(row)))
        if col >= 0:
            field_name = COLUMNS[col]
            menu.addAction(
                Action(FIF.COPY, f"Copia {field_name}", triggered=lambda: self._copy_field(row, col))
            )
        menu.addSeparator()
        menu.addAction(Action(FIF.EDIT, "Modifica", triggered=lambda: self.edit_requested.emit(member)))
        menu.addAction(
            Action(FIF.MOVE, "Sposta in un'altra lista", triggered=lambda: self.move_requested.emit(member))
        )
        menu.addSeparator()
        menu.addAction(Action(FIF.DELETE, "Elimina", triggered=lambda: self.delete_requested.emit(member)))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _copy_row(self, row: int) -> None:
        values = [self.table.item(row, col).text() for col in range(self.table.columnCount())]
        QGuiApplication.clipboard().setText("\t".join(values))

    def _copy_field(self, row: int, col: int) -> None:
        QGuiApplication.clipboard().setText(self.table.item(row, col).text())
