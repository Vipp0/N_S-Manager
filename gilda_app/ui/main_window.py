import sqlite3
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog
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
    set_setting,
    update_member,
)
from gilda_app.i18n import tr
from gilda_app.importer.excel_export import export_workbook
from gilda_app.importer.excel_import import import_row, parse_workbook
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO, Member, status_label
from gilda_app.ui.import_dialog import ImportPreviewDialog
from gilda_app.ui.member_dialog import MemberDialog
from gilda_app.ui.member_table import MemberListPage
from gilda_app.ui.move_dialog import MoveDialog
from gilda_app.ui.progress_dialog import ImportProgressDialog
from gilda_app.ui.reset_dialog import ResetConfirmDialog
from gilda_app.ui.settings_page import SettingsPage
from gilda_app.ui.stats_view import StatsPage
from gilda_app.utils.icons import ban_icon
from gilda_app.utils.restart import restart_app

STATUS_ORDER = [STATUS_ATTIVO, STATUS_EX_MEMBRO, STATUS_BANNATO]


class MainWindow(FluentWindow):
    def __init__(self, conn: sqlite3.Connection, db_path: Path):
        super().__init__()
        self.conn = conn
        self.db_path = db_path

        self.setWindowTitle(tr("window.title"))
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

        icons = {STATUS_ATTIVO: FIF.PEOPLE, STATUS_EX_MEMBRO: FIF.HISTORY, STATUS_BANNATO: ban_icon()}
        for status in STATUS_ORDER:
            self.addSubInterface(self.pages[status], icons[status], status_label(status))

        self.stats_page = StatsPage(lambda: self.conn, self)
        self.stats_page.setObjectName("page_stats")
        self.addSubInterface(self.stats_page, FIF.PIE_SINGLE, tr("nav.stats"))

        self.settings_page = SettingsPage(self)
        self.settings_page.setObjectName("page_settings")
        self.settings_page.import_requested.connect(self._on_import)
        self.settings_page.export_requested.connect(self._on_export)
        self.settings_page.reset_requested.connect(self._on_reset)
        self.settings_page.language_changed.connect(self._on_language_changed)
        self.addSubInterface(self.settings_page, FIF.SETTING, tr("nav.settings"), NavigationItemPosition.BOTTOM)

        self.navigationInterface.setCurrentItem(self.pages[STATUS_ATTIVO].objectName())
        self.refresh_all()

    # -- refresh -----------------------------------------------------
    def refresh_all(self) -> None:
        for status, page in self.pages.items():
            page.set_members(get_members(self.conn, status))
        self.stats_page.refresh()

    def _on_language_changed(self, lang_code: str) -> None:
        set_setting(self.conn, "language", lang_code)
        box = MessageBox(tr("dialog.restart.title"), tr("dialog.restart.body"), self)
        box.yesButton.setText(tr("button.restart_now"))
        box.cancelButton.setText(tr("button.later"))
        if box.exec():
            self.conn.close()
            restart_app()

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
                data_inserimento=values["data_inserimento"],
            )
            self.refresh_all()
            self._notify(
                tr("notify.member_added.title"),
                tr("notify.member_added.body", name=values["family_name"], status=status_label(status)),
            )

    def _on_edit(self, member: Member) -> None:
        dialog = MemberDialog(self, member=member, conn=self.conn)
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
                data_inserimento=values["data_inserimento"],
                update_date=True,
            )
            self.refresh_all()
            self._notify(
                tr("notify.member_updated.title"),
                tr("notify.member_updated.body", name=values["family_name"]),
            )

    def _on_delete(self, member: Member) -> None:
        box = MessageBox(
            tr("dialog.delete.title"),
            tr("dialog.delete.body", name=member.family_name, main=member.main_name),
            self,
        )
        if box.exec():
            delete_member(self.conn, member.id)
            self.refresh_all()
            self._notify(tr("notify.member_deleted.title"), tr("notify.member_deleted.body", name=member.family_name))

    def _on_move(self, member: Member) -> None:
        dialog = MoveDialog(self, member=member)
        if dialog.exec():
            target = dialog.target_status()
            note = dialog.note()
            backup_database(self.db_path, "move")
            move_member_status(self.conn, member.id, target, note=note)
            self.refresh_all()
            self._notify(
                tr("notify.member_moved.title"),
                tr("notify.member_moved.body", name=member.family_name, status=status_label(target)),
            )

    # -- Import / Export / Reset ---------------------------------------
    def _on_import(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(self, tr("dialog.pick_import_file"), "", "Excel (*.xlsx)")
        if not path_str:
            return
        path = Path(path_str)
        try:
            preview = parse_workbook(path)
        except (KeyError, OSError) as exc:
            self._notify(tr("notify.import_failed.title"), tr("notify.import_failed.body", error=exc), error=True)
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
        total = len(preview.rows)

        progress = ImportProgressDialog(self)
        progress.show()
        QApplication.processEvents()
        try:
            for i, row in enumerate(preview.rows, start=1):
                result = import_row(self.conn, row, on_duplicate=policy, commit=False)
                outcome[result] = outcome.get(result, 0) + 1
                if i % 10 == 0 or i == total:
                    progress.set_progress(i, total)
                    QApplication.processEvents()
            self.conn.commit()
        finally:
            progress.close()

        self.refresh_all()
        self._notify(
            tr("notify.import_done.title"),
            tr(
                "notify.import_done.body",
                inserted=outcome.get("inserted", 0),
                updated=outcome.get("updated", 0),
                skipped=outcome.get("skipped", 0),
            ),
        )

    def _on_export(self) -> None:
        path_str, _ = QFileDialog.getSaveFileName(self, tr("dialog.pick_export_file"), "gilda_export.xlsx", "Excel (*.xlsx)")
        if not path_str:
            return
        try:
            export_workbook(self.conn, Path(path_str))
        except OSError as exc:
            self._notify(tr("notify.export_failed.title"), str(exc), error=True)
            return
        self._notify(tr("notify.export_done.title"), tr("notify.export_done.body", path=path_str))

    def _on_reset(self) -> None:
        warn = MessageBox(tr("dialog.reset_warn.title"), tr("dialog.reset_warn.body"), self)
        if not warn.exec():
            return

        confirm = ResetConfirmDialog(self)
        if not confirm.exec():
            return

        backup_database(self.db_path, "reset")
        reset_database(self.conn)
        self.refresh_all()
        self._notify(tr("notify.reset_done.title"), tr("notify.reset_done.body"))
