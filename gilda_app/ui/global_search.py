import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem
from qfluentwidgets import MessageBoxBase, SearchLineEdit, SubtitleLabel

from gilda_app.db.database import get_members
from gilda_app.i18n import tr
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO, status_label
from gilda_app.utils.flags import nations_text

ALL_STATUSES = [STATUS_ATTIVO, STATUS_EX_MEMBRO, STATUS_BANNATO]


class GlobalSearchDialog(MessageBoxBase):
    """Cerca un membro per nome/nazione/discord in tutte e 3 le liste insieme, per
    quando non si ricorda se è ancora attivo, uscito o bannato. La ricerca per singola
    scheda resta com'era: qui si copre solo il caso "non so dove guardare"."""

    def __init__(self, parent, conn: sqlite3.Connection):
        super().__init__(parent)
        self.conn = conn
        self._result_ids: list[tuple[str, int]] = []

        self.titleLabel = SubtitleLabel(tr("search.global.title"), self)
        self.viewLayout.addWidget(self.titleLabel)

        self.search_box = SearchLineEdit(self)
        self.search_box.setPlaceholderText(tr("search.global.placeholder"))
        self.search_box.textChanged.connect(self._run_search)
        self.viewLayout.addWidget(self.search_box)

        self.results_table = QTableWidget(self)
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(
            [
                tr("column.family_name"),
                tr("column.main_name"),
                tr("column.nation"),
                tr("column.discord_name"),
                tr("search.global.column.status"),
            ]
        )
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.verticalHeader().hide()
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.results_table.setMinimumHeight(280)
        self.results_table.itemSelectionChanged.connect(self._update_button_state)
        self.results_table.doubleClicked.connect(self._on_double_click)
        self.viewLayout.addWidget(self.results_table)

        self.widget.setMinimumWidth(560)
        self.yesButton.setText(tr("search.global.go"))
        self.cancelButton.setText(tr("button.close"))
        self._update_button_state()
        self.search_box.setFocus()

    def _run_search(self, text: str) -> None:
        text = text.strip().lower()
        self.results_table.setRowCount(0)
        self._result_ids = []
        if not text:
            self._update_button_state()
            return

        for status in ALL_STATUSES:
            for member in get_members(self.conn, status):
                nation_text = nations_text(member.nations)
                haystacks = [member.family_name, member.main_name, member.discord_name, nation_text]
                if not any(text in (h or "").lower() for h in haystacks):
                    continue

                row = self.results_table.rowCount()
                self.results_table.insertRow(row)
                values = [member.family_name, member.main_name, nation_text, member.discord_name, status_label(status)]
                for col, value in enumerate(values):
                    self.results_table.setItem(row, col, QTableWidgetItem(value))
                self._result_ids.append((status, member.id))

        self._update_button_state()

    def _on_double_click(self, _index) -> None:
        if self.results_table.currentRow() >= 0:
            self.accept()

    def _update_button_state(self) -> None:
        self.yesButton.setEnabled(self.results_table.currentRow() >= 0)

    def selected_member(self) -> tuple[str, int] | None:
        row = self.results_table.currentRow()
        if row < 0 or row >= len(self._result_ids):
            return None
        return self._result_ids[row]
