from datetime import date
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import Action, FluentIcon as FIF
from qfluentwidgets import PrimaryPushButton, RoundMenu, StrongBodyLabel, TableWidget

from gilda_app.i18n import tr
from gilda_app.models.member import Member, STATUS_EX_MEMBRO, status_label
from gilda_app.ui.member_detail_panel import PANEL_WIDTH, MemberDetailPanel
from gilda_app.ui.persistent_clear_search import PersistentClearSearchLineEdit
from gilda_app.utils.discord_format import discord_copy_text
from gilda_app.utils.flags import MAX_FLAG_ICON_SIZE, combined_flag_icon, nations_text
from gilda_app.utils.member_summary import summarize
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


HEADER_DECOR_HEIGHT = 70  # decorazioni ai lati del logo, nelle liste
HEADER_DECOR_MIN_WIDTH = 1250  # sotto questa larghezza della pagina non c'è spazio ai lati del logo
PANEL_BESIDE_MIN_WIDTH = 1200  # da questa larghezza il pannello dei dettagli sta accanto alla tabella, sotto la copre


class MemberListPage(QWidget):
    """Tabella + ricerca per una singola lista (Attuali / Ex membri / Bannati)."""

    edit_requested = Signal(object)
    move_requested = Signal(object)
    delete_requested = Signal(object)
    add_requested = Signal(str)

    def __init__(self, status: str, parent=None, history_provider: Callable[[int], list] | None = None):
        """history_provider: dato l'id di un membro, le righe della sua cronologia (status_history), per il pannello."""
        super().__init__(parent)
        self.status = status
        self._history_provider = history_provider
        self._members: list[Member] = []
        self._old_names: dict[int, list[str]] = {}
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
        self._wordmark = None  # il logo può cambiare nei periodi di festa: vedi set_wordmark
        if WORDMARK_PATH.exists():
            wordmark = QLabel(self)
            self._wordmark = wordmark
            # 86 invece di 56: a schermo intero restava troppo piccolo rispetto allo
            # spazio vuoto dell'intestazione. 86px riporta la larghezza (~290px) vicina
            # a quella del vecchio wordmark orizzontale, nonostante la forma più quadrata.
            wordmark.setPixmap(QPixmap(str(WORDMARK_PATH)).scaledToHeight(86, Qt.SmoothTransformation))
            # Ai lati del logo, solo nei temi stagionali (vedi set_decor): nascosti se la finestra è stretta.
            self._decor_left, self._decor_right = QLabel(self), QLabel(self)
            for label in (self._decor_left, self._decor_right):
                label.hide()
            header.addWidget(self._decor_left)
            header.addWidget(wordmark)
            header.addWidget(self._decor_right)
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
        # Il pannello dei dettagli a destra: si apre con un clic su una riga (vedi _on_table_release).
        self._body = QHBoxLayout()
        self._body.setSpacing(16)
        self._body.addWidget(self.table, 1)
        layout.addLayout(self._body, 1)
        self.detail = MemberDetailPanel(self)
        self.detail.hide()
        self.detail.close_requested.connect(self.close_detail)
        self.detail.edit_requested.connect(self.edit_requested)
        self.detail.move_requested.connect(self.move_requested)
        shadow = QGraphicsDropShadowEffect(self.detail)  # si vede solo quando il pannello copre la tabella
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 70))
        self._detail_shadow = shadow
        self._detail_id: int | None = None
        self._ignore_next_release = False  # dopo un doppio clic (modifica) il rilascio non deve richiudere
        self._open_at_press: int | None = None  # il membro mostrato nel pannello quando si preme il mouse
        self.table.viewport().installEventFilter(self)
        self.table.itemSelectionChanged.connect(self._follow_selection)
        QShortcut(QKeySequence(Qt.Key_Escape), self.table, activated=self.close_detail)

    def set_decor(self, season) -> None:
        """Decorazioni ai lati del logo (None = nessuna); a ogni tema le sue, se ci sono i file."""
        if self._wordmark is None:
            return
        for label, name in ((self._decor_left, "header_left"), (self._decor_right, "header_right")):
            path = season.decor_path(name) if season is not None else None
            if path is not None and path.exists():
                label.setPixmap(QPixmap(str(path)).scaledToHeight(HEADER_DECOR_HEIGHT, Qt.SmoothTransformation))
            else:
                label.clear()
        self._update_decor_visibility()

    def _update_decor_visibility(self) -> None:
        show = self.width() >= HEADER_DECOR_MIN_WIDTH
        for label in (self._decor_left, self._decor_right):
            label.setVisible(show and label.pixmap() is not None and not label.pixmap().isNull())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._wordmark is not None:
            self._update_decor_visibility()
        self._place_detail()

    def mousePressEvent(self, event) -> None:
        """Un clic in un punto vuoto della pagina (fuori da tabella e pannello) chiude il pannello."""
        if event.button() == Qt.LeftButton:
            self.close_detail()
        super().mousePressEvent(event)

    def set_wordmark(self, path: Path) -> None:
        """Cambia il logo dell'intestazione (tema stagionale); se il file manca non fa niente."""
        if self._wordmark is not None and path.exists():
            self._wordmark.setPixmap(QPixmap(str(path)).scaledToHeight(86, Qt.SmoothTransformation))

    def set_members(self, members: list[Member], old_names: dict[int, list[str]] | None = None) -> None:
        self._members = members
        self._old_names = old_names or {}
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
        self._refresh_detail()

    def eventFilter(self, obj, event) -> bool:
        if obj is self.table.viewport():
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                # Prima che Qt scelga la riga (e il pannello la segua): serve a distinguere un secondo clic sulla
                # stessa riga (chiude) dal clic su un'altra (cambia membro).
                self._open_at_press = self._detail_id if self.detail.isVisible() else None
            elif event.type() == QEvent.MouseButtonDblClick:
                self._ignore_next_release = True  # il doppio clic modifica: il clic non deve aprire o chiudere il pannello
            elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                if self._ignore_next_release:
                    self._ignore_next_release = False
                else:
                    self._on_table_release(event.pos())
            return False
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
            if not match:
                # I vecchi nomi non sono una colonna, ma la ricerca deve trovarli lo stesso.
                member_id = self.table.item(row, NUMBER_COLUMN).data(Qt.UserRole)
                match = any(text in name.lower() for name in self._old_names.get(member_id, []))
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

    # -- pannello dei dettagli ------------------------------------------------------------------------
    def _on_table_release(self, pos: QPoint) -> None:
        """Clic su una riga: apre il pannello; sulla stessa riga di nuovo: lo chiude; in un punto vuoto: lo chiude."""
        row = self.table.rowAt(pos.y())
        member = self._member_at_row(row) if row >= 0 else None
        if member is None or member.id == self._open_at_press:
            self.close_detail()
        else:
            self.open_detail(member)

    def open_detail(self, member: Member) -> None:
        self._detail_id = member.id
        self._open_at_press = None
        self._fill_detail(member)
        self.detail.show()
        self._place_detail()

    def close_detail(self) -> None:
        if not self.detail.isVisible():
            return
        self.detail.hide()
        self._detail_id = None
        self.table.clearSelection()
        self._place_detail()

    def _fill_detail(self, member: Member) -> None:
        history = self._history_provider(member.id) if self._history_provider is not None else []
        self.detail.set_member(member, summarize(member, history, date.today()))

    def _refresh_detail(self) -> None:
        """Dopo un aggiornamento dei dati il pannello mostra quelli nuovi (o si chiude se il membro non c'è più)."""
        if not self.detail.isVisible():
            return
        member = next((m for m in self._members if m.id == self._detail_id), None)
        if member is None:
            self.close_detail()
            return
        self._fill_detail(member)
        for row in range(self.table.rowCount()):  # l'aggiornamento azzera la selezione: si rimette sul membro
            item = self.table.item(row, NUMBER_COLUMN)
            if item is not None and item.data(Qt.UserRole) == member.id:
                self.table.selectRow(row)
                break

    def _follow_selection(self) -> None:
        """Con il pannello aperto, scegliere un'altra riga (anche con la tastiera o il tasto destro) lo aggiorna."""
        if not self.detail.isVisible():
            return
        rows = self.table.selectionModel().selectedRows()
        member = self._member_at_row(rows[0].row()) if rows else None
        if member is not None and member.id != self._detail_id:
            self.open_detail(member)

    def _place_detail(self) -> None:
        """Larga: il pannello sta accanto alla tabella e la restringe. Stretta: la copre sul lato destro, senza
        toglierle spazio."""
        beside = self.width() >= PANEL_BESIDE_MIN_WIDTH
        in_layout = self._body.indexOf(self.detail) >= 0
        if beside and not in_layout:
            self.detail.setGraphicsEffect(None)
            self._body.addWidget(self.detail)
        elif not beside and in_layout:
            self._body.removeWidget(self.detail)
        if not beside:
            top_left = self.table.mapTo(self, QPoint(0, 0))
            height = self.table.height()
            self.detail.setGraphicsEffect(self._detail_shadow)
            self.detail.setGeometry(QRect(self.width() - 24 - PANEL_WIDTH, top_left.y(), PANEL_WIDTH, height))
            self.detail.raise_()

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
