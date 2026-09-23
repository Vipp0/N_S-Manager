from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPixmap
from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QLabel, QTableWidgetItem, QVBoxLayout, QWidget
from qfluentwidgets import Action, FluentIcon as FIF
from qfluentwidgets import PrimaryPushButton, RoundMenu, StrongBodyLabel, TableWidget

from gilda_app.i18n import tr
from gilda_app.models.member import Member, STATUS_EX_MEMBRO, status_label
from gilda_app.ui.persistent_clear_search import PersistentClearSearchLineEdit
from gilda_app.utils.discord_format import discord_copy_text
from gilda_app.utils.flags import MAX_FLAG_ICON_SIZE, combined_flag_icon, nations_text
from gilda_app.utils.scrollbar import widen_scrollbar_on_hover

NUMBER_COLUMN = 0
NATION_COLUMN = 3
STILL_ON_DISCORD_COLOR = QColor("#1a7f37")
TABLE_FONT = QFont("Segoe UI", 14)
HEADER_FONT = QFont("Segoe UI", 14, QFont.DemiBold)
WORDMARK_PATH = Path(__file__).resolve().parent.parent / "resources" / "wordmark.png"


def _columns(status: str) -> list[str]:
    cols = [
        tr("column.number"),
        tr("column.family_name"),
        tr("column.main_name"),
        tr("column.nation"),
        tr("column.discord_name"),
    ]
    # Ha senso solo per gli ex membri: se sono ancora presenti nel canale Discord della
    # gilda pur avendola lasciata in gioco. Non mostrata nelle altre due liste.
    if status == STATUS_EX_MEMBRO:
        cols.append(tr("column.still_on_discord"))
    cols.append(tr("column.note"))
    return cols


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
        self._columns = _columns(status)
        self._still_on_discord_col = self._columns.index(tr("column.still_on_discord")) if status == STATUS_EX_MEMBRO else None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = StrongBodyLabel(status_label(status), self)
        self.search_box = PersistentClearSearchLineEdit(self)
        self.search_box.setPlaceholderText(tr("search.placeholder"))
        self.search_box.setFixedWidth(320)
        self.search_box.textChanged.connect(self._apply_filter)
        add_btn = PrimaryPushButton(FIF.ADD, tr("button.add_member"), self)
        add_btn.clicked.connect(lambda: self.add_requested.emit(self.status))
        header.addWidget(title)
        header.addStretch(1)
        # Wordmark della gilda al centro dell'intestazione, tra il nome della lista
        # (a sinistra) e la barra di ricerca (a destra).
        if WORDMARK_PATH.exists():
            wordmark = QLabel(self)
            # 86 invece di 56: a schermo intero restava troppo piccolo rispetto allo
            # spazio vuoto dell'intestazione. 86px riporta la larghezza (~290px) vicina
            # a quella del vecchio wordmark orizzontale, nonostante la forma più quadrata.
            wordmark.setPixmap(QPixmap(str(WORDMARK_PATH)).scaledToHeight(86, Qt.SmoothTransformation))
            header.addWidget(wordmark)
            header.addStretch(1)
        header.addWidget(self.search_box)
        header.addWidget(add_btn)
        layout.addLayout(header)

        self.table = TableWidget(self)
        self.table.setColumnCount(len(self._columns))
        self.table.setHorizontalHeaderLabels(self._columns)
        self.table.setFont(TABLE_FONT)
        self.table.horizontalHeader().setFont(HEADER_FONT)
        self.table.verticalHeader().setDefaultSectionSize(52)
        # Stessa dimensione della bandiera combinata più grande possibile (2 bandiere
        # affiancate): così Qt non deve scalare l'icona (altrimenti risulterebbe sfocata
        # o, di default, troppo piccola visto che l'iconSize di base di Qt è 16x16).
        self.table.setIconSize(QSize(*MAX_FLAG_ICON_SIZE))
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicator(1, Qt.AscendingOrder)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(True)
        # La colonna N. è un identificativo fisso del membro (posizione nell'elenco
        # alfabetico al momento del caricamento), non ha senso ordinarci la tabella:
        # un event filter sul viewport dell'header (dove arrivano davvero gli eventi
        # mouse, essendo QHeaderView un QAbstractItemView) intercetta e ignora i click
        # su questa colonna prima che raggiungano l'ordinamento automatico di Qt.
        self.table.horizontalHeader().viewport().installEventFilter(self)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._on_double_click)
        widen_scrollbar_on_hover(self.table.scrollDelagate.vScrollBar)
        layout.addWidget(self.table)

    def set_members(self, members: list[Member]) -> None:
        self._members = members
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(members))
        for row, member in enumerate(members):
            values = [
                str(row + 1),
                member.family_name,
                member.main_name,
                nations_text(member.nations),
                member.discord_name,
            ]
            if self._still_on_discord_col is not None:
                values.append("")
            values.append(member.note or "")
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, member.id)
                self.table.setItem(row, col, item)

            icon = combined_flag_icon(member.nations)
            if icon is not None:
                self.table.item(row, NATION_COLUMN).setIcon(icon)

            if self._still_on_discord_col is not None and member.still_on_discord:
                check_item = self.table.item(row, self._still_on_discord_col)
                check_item.setText("✓")
                check_item.setTextAlignment(Qt.AlignCenter)
                check_item.setForeground(STILL_ON_DISCORD_COLOR)
                bold_font = QFont(check_item.font())
                bold_font.setBold(True)
                check_item.setFont(bold_font)

        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        self._apply_filter(self.search_box.text())

    def eventFilter(self, obj, event) -> bool:
        if obj is self.table.horizontalHeader().viewport() and event.type() in (
            QEvent.MouseButtonPress,
            QEvent.MouseButtonRelease,
            QEvent.MouseButtonDblClick,
        ):
            if self.table.horizontalHeader().logicalIndexAt(event.pos()) == NUMBER_COLUMN:
                return True
        return super().eventFilter(obj, event)

    def _apply_filter(self, text: str) -> None:
        text = text.strip().lower()
        for row in range(self.table.rowCount()):
            if not text:
                self.table.setRowHidden(row, False)
                continue
            match = any(
                text in (self.table.item(row, col).text().lower())
                for col in range(1, self.table.columnCount())
                if self.table.item(row, col) is not None
            )
            self.table.setRowHidden(row, not match)

    def _member_at_row(self, row: int) -> Member | None:
        item = self.table.item(row, NUMBER_COLUMN)
        if item is None:
            return None
        member_id = item.data(Qt.UserRole)
        return next((m for m in self._members if m.id == member_id), None)

    def select_member_by_id(self, member_id: int) -> None:
        """Seleziona e mostra la riga di un membro (usato dalla ricerca globale per
        saltare direttamente al risultato): azzera un eventuale filtro locale attivo,
        perché altrimenti la riga cercata potrebbe restare nascosta."""
        self.search_box.clear()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, NUMBER_COLUMN)
            if item is not None and item.data(Qt.UserRole) == member_id:
                self.table.selectRow(row)
                self.table.scrollToItem(item)
                break

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
        menu.addAction(Action(FIF.COPY, tr("menu.copy_row"), triggered=lambda: self._copy_row(row)))
        if col >= 0:
            field_name = self._columns[col]
            menu.addAction(
                Action(FIF.COPY, tr("menu.copy_field", field=field_name), triggered=lambda: self._copy_field(row, col))
            )
        menu.addAction(
            Action(FIF.SEND_FILL, tr("menu.copy_discord"), triggered=lambda: self._copy_discord(member))
        )
        menu.addSeparator()
        menu.addAction(Action(FIF.EDIT, tr("menu.edit"), triggered=lambda: self.edit_requested.emit(member)))
        menu.addAction(
            Action(FIF.MOVE, tr("menu.move"), triggered=lambda: self.move_requested.emit(member))
        )
        menu.addSeparator()
        menu.addAction(Action(FIF.DELETE, tr("menu.delete"), triggered=lambda: self.delete_requested.emit(member)))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _copy_row(self, row: int) -> None:
        values = [self.table.item(row, col).text() for col in range(self.table.columnCount())]
        QGuiApplication.clipboard().setText("\t".join(values))

    def _copy_field(self, row: int, col: int) -> None:
        QGuiApplication.clipboard().setText(self.table.item(row, col).text())

    def _copy_discord(self, member: Member) -> None:
        QGuiApplication.clipboard().setText(discord_copy_text(member))
