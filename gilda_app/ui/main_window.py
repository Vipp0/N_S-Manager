import sqlite3
from pathlib import Path

from PySide6.QtWidgets import QFileDialog
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import FluentWindow, InfoBar, InfoBarPosition, MessageBox, NavigationItemPosition

from gilda_app.db.backup import backup_database
from gilda_app.db.database import (
    add_member,
    delete_member,
    find_duplicate,
    get_members,
    move_member_status,
    reset_database,
    update_member,
)
from gilda_app.importer.excel_export import export_workbook
from gilda_app.importer.excel_import import import_row, parse_workbook
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO, STATUS_LABELS, Member
from gilda_app.ui.import_dialog import ImportPreviewDialog
from gilda_app.ui.member_dialog import MemberDialog
from gilda_app.ui.member_table import MemberListPage
from gilda_app.ui.move_dialog import MoveDialog
from gilda_app.ui.reset_dialog import ResetConfirmDialog
from gilda_app.ui.settings_page import SettingsPage
from gilda_app.ui.stats_view import StatsPage

STATUS_ORDER = [STATUS_ATTIVO, STATUS_EX_MEMBRO, STATUS_BANNATO]


class MainWindow(FluentWindow):
    def __init__(self, conn: sqlite3.Connection, db_path: Path):
        super().__init__()
        self.conn = conn
        self.db_path = db_path

        self.setWindowTitle("Gestionale Membri Gilda")
        self.resize(1100, 720)

        self.pages: dict[str, MemberListPage] = {}
        for status in STATUS_ORDER:
            page = MemberListPage(status, self)
            page.setObjectName(f"page_{status}")
            page.edit_requested.connect(self._on_edit)
            page.move_requested.connect(self._on_move)
            page.delete_requested.connect(self._on_delete)
            page.add_requested.connect(self._on_add)
            self.pages[status] = page

        icons = {STATUS_ATTIVO: FIF.PEOPLE, STATUS_EX_MEMBRO: FIF.HISTORY, STATUS_BANNATO: FIF.REMOVE}
        for status in STATUS_ORDER:
            self.addSubInterface(self.pages[status], icons[status], STATUS_LABELS[status])

        self.stats_page = StatsPage(lambda: self.conn, self)
        self.stats_page.setObjectName("page_stats")
        self.addSubInterface(self.stats_page, FIF.PIE_SINGLE, "Statistiche")

        self.settings_page = SettingsPage(self)
        self.settings_page.setObjectName("page_settings")
        self.settings_page.import_requested.connect(self._on_import)
        self.settings_page.export_requested.connect(self._on_export)
        self.settings_page.reset_requested.connect(self._on_reset)
        self.addSubInterface(self.settings_page, FIF.SETTING, "Impostazioni", NavigationItemPosition.BOTTOM)

        self.navigationInterface.setCurrentItem(self.pages[STATUS_ATTIVO].objectName())
        self.refresh_all()

    # -- refresh -----------------------------------------------------
    def refresh_all(self) -> None:
        for status, page in self.pages.items():
            page.set_members(get_members(self.conn, status))
        self.stats_page.refresh()

    def _notify(self, title: str, content: str, error: bool = False) -> None:
        method = InfoBar.error if error else InfoBar.success
        method(
            title=title,
            content=content,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3500,
            parent=self,
        )

    # -- CRUD ----------------------------------------------------------
    def _on_add(self, status: str) -> None:
        dialog = MemberDialog(self, member=None)
        if dialog.exec():
            values = dialog.values()
            add_member(
                self.conn,
                family_name=values["family_name"],
                main_name=values["main_name"],
                discord_name=values["discord_name"],
                nations=values["nations"],
                status=status,
                note=values["note"],
            )
            self.refresh_all()
            self._notify("Membro aggiunto", f"{values['family_name']} aggiunto a {STATUS_LABELS[status]}.")

    def _on_edit(self, member: Member) -> None:
        dialog = MemberDialog(self, member=member)
        if dialog.exec():
            values = dialog.values()
            update_member(
                self.conn,
                member.id,
                family_name=values["family_name"],
                main_name=values["main_name"],
                discord_name=values["discord_name"],
                nations=values["nations"],
                note=values["note"],
            )
            self.refresh_all()
            self._notify("Membro aggiornato", f"{values['family_name']} è stato aggiornato.")

    def _on_delete(self, member: Member) -> None:
        box = MessageBox(
            "Elimina membro",
            f"Eliminare definitivamente {member.family_name} ({member.main_name})? "
            "L'azione non è reversibile.",
            self,
        )
        if box.exec():
            delete_member(self.conn, member.id)
            self.refresh_all()
            self._notify("Membro eliminato", f"{member.family_name} è stato eliminato.")

    def _on_move(self, member: Member) -> None:
        dialog = MoveDialog(self, member=member)
        if dialog.exec():
            target = dialog.target_status()
            note = dialog.note()
            backup_database(self.db_path, "move")
            move_member_status(self.conn, member.id, target, note=note)
            self.refresh_all()
            self._notify(
                "Membro spostato",
                f"{member.family_name} spostato in {STATUS_LABELS[target]}.",
            )

    # -- Import / Export / Reset ---------------------------------------
    def _on_import(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(self, "Seleziona file Excel da importare", "", "Excel (*.xlsx)")
        if not path_str:
            return
        path = Path(path_str)
        try:
            preview = parse_workbook(path)
        except (KeyError, OSError) as exc:
            self._notify("Import fallito", f"Impossibile leggere il file: {exc}", error=True)
            return

        duplicate_count = sum(
            1 for row in preview.rows if find_duplicate(self.conn, row.family_name, row.main_name) is not None
        )

        dialog = ImportPreviewDialog(self, preview, duplicate_count)
        if not dialog.exec():
            return

        backup_database(self.db_path, "import")
        policy = dialog.duplicate_policy()
        outcome = {"inserted": 0, "updated": 0, "skipped": 0}
        for row in preview.rows:
            result = import_row(self.conn, row, on_duplicate=policy)
            outcome[result if result != "skipped" else "skipped"] = outcome.get(result, 0) + 1

        self.refresh_all()
        self._notify(
            "Import completato",
            f"Inseriti: {outcome.get('inserted', 0)} · Aggiornati: {outcome.get('updated', 0)} · "
            f"Saltati: {outcome.get('skipped', 0)}",
        )

    def _on_export(self) -> None:
        path_str, _ = QFileDialog.getSaveFileName(self, "Esporta in Excel", "gilda_export.xlsx", "Excel (*.xlsx)")
        if not path_str:
            return
        try:
            export_workbook(self.conn, Path(path_str))
        except OSError as exc:
            self._notify("Export fallito", str(exc), error=True)
            return
        self._notify("Export completato", f"File salvato in {path_str}")

    def _on_reset(self) -> None:
        warn = MessageBox(
            "Azzera database",
            "Stai per eliminare TUTTI i membri e lo storico movimenti. Questa è la prima delle due conferme richieste.",
            self,
        )
        if not warn.exec():
            return

        confirm = ResetConfirmDialog(self)
        if not confirm.exec():
            return

        backup_database(self.db_path, "reset")
        reset_database(self.conn)
        self.refresh_all()
        self._notify("Database azzerato", "Tutti i dati sono stati eliminati. Backup salvato in backups/.")
