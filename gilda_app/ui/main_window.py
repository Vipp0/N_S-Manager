import sqlite3
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QFileDialog
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import FluentWindow, InfoBar, InfoBarPosition, MessageBox, NavigationItemPosition, TransparentToolButton

from gilda_app.db.backup import (
    EXTRA_DIR_SETTING,
    backup_database,
    is_valid_backup,
    list_backups,
    restore_backup,
)
from gilda_app.db.holidays import refresh_holidays_if_needed
from gilda_app.db.database import (
    add_member,
    connect,
    delete_member,
    find_duplicate,
    get_members,
    get_setting,
    move_member_status,
    reset_database,
    set_setting,
    update_member,
)
from gilda_app.i18n import tr
from gilda_app.importer.excel_export import export_workbook
from gilda_app.importer.excel_import import find_intra_file_duplicates, import_row, parse_workbook
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO, Member, status_label
from gilda_app.ui.calendar_page import CalendarPage
from gilda_app.ui.changelog_dialog import ChangelogDialog
from gilda_app.ui.global_search import GlobalSearchDialog
from gilda_app.ui.import_dialog import ImportPreviewDialog
from gilda_app.ui.member_dialog import MemberDialog
from gilda_app.ui.member_table import MemberListPage
from gilda_app.ui.move_dialog import MoveDialog
from gilda_app.ui.notes_page import NotesPage
from gilda_app.ui.progress_dialog import ImportProgressDialog
from gilda_app.ui.reset_dialog import ResetConfirmDialog
from gilda_app.ui.restore_dialog import RestoreBackupDialog, format_backup_when
from gilda_app.ui.settings_page import SettingsPage
from gilda_app.ui.stats_view import StatsPage
from gilda_app.utils.discord_format import discord_copy_text
from gilda_app.version import __version__
from gilda_app.utils.icons import ban_icon
from gilda_app.utils.paths import backups_dir
from gilda_app.utils.restart import restart_app
from gilda_app.utils.update_check import RELEASES_PAGE_URL, fetch_latest_release_tag, is_newer

STATUS_ORDER = [STATUS_ATTIVO, STATUS_EX_MEMBRO, STATUS_BANNATO]
APP_ICON_PATH = Path(__file__).resolve().parent.parent / "resources" / "app_icon.png"
UPDATE_NOTIFIED_SETTING = "update_notified_version"


class _HolidayRefreshSignal(QObject):
    """Ponte verso il thread Qt: un segnale può essere emesso da un altro thread in
    sicurezza, una chiamata diretta a un widget no."""

    finished = Signal(bool)


class _UpdateCheckSignal(QObject):
    finished = Signal(str)


class MainWindow(FluentWindow):
    def __init__(self, conn: sqlite3.Connection, db_path: Path):
        super().__init__()
        self.conn = conn
        self.db_path = db_path

        self.setWindowTitle(f"{tr('window.title')} v{__version__}")
        self.resize(1100, 720)
        self._setup_title_bar()
        QShortcut(QKeySequence.Find, self, activated=self._on_global_search)

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

        self.notes_page = NotesPage(lambda: self.conn, self)
        self.notes_page.setObjectName("page_notes")
        self.addSubInterface(self.notes_page, FIF.QUICK_NOTE, tr("nav.notes"))

        self.calendar_page = CalendarPage(lambda: self.conn, self)
        self.calendar_page.setObjectName("page_calendar")
        self.addSubInterface(self.calendar_page, FIF.CALENDAR, tr("nav.calendar"))
        self._start_holiday_refresh()
        self._start_update_check()

        self.stats_page = StatsPage(lambda: self.conn, self._open_nation_in_current, self)
        self.stats_page.setObjectName("page_stats")
        self.addSubInterface(self.stats_page, FIF.PIE_SINGLE, tr("nav.stats"))

        self.settings_page = SettingsPage(self)
        self.settings_page.setObjectName("page_settings")
        self.settings_page.import_requested.connect(self._on_import)
        self.settings_page.export_requested.connect(self._on_export)
        self.settings_page.reset_requested.connect(self._on_reset)
        self.settings_page.language_changed.connect(self._on_language_changed)
        self.settings_page.backup_now_requested.connect(self._on_backup_now)
        self.settings_page.open_backups_requested.connect(self._on_open_backups)
        self.settings_page.restore_requested.connect(self._on_restore)
        self.settings_page.extra_dir_pick_requested.connect(self._on_pick_extra_dir)
        self.settings_page.extra_dir_clear_requested.connect(self._on_clear_extra_dir)
        self.settings_page.changelog_requested.connect(self._on_changelog)
        self.settings_page.set_extra_backup_dir(get_setting(self.conn, EXTRA_DIR_SETTING))
        self.addSubInterface(self.settings_page, FIF.SETTING, tr("nav.settings"), NavigationItemPosition.BOTTOM)

        self.navigationInterface.setCurrentItem(self.pages[STATUS_ATTIVO].objectName())
        self.refresh_all()

    def closeEvent(self, event) -> None:
        # Il blocco note salva con un ritardo dopo l'ultima battitura: se si chiude
        # l'app proprio in quella finestra andrebbero perse le ultime modifiche.
        self.notes_page.save()
        super().closeEvent(event)

    def _setup_title_bar(self) -> None:
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
            # FluentTitleBar.iconLabel (la piccola icona nell'angolo in alto a
            # sinistra della title bar) si aggiorna da solo alla windowIcon, non
            # serve altro codice per quella.

        # Il titolo testuale ("Night_Shade Manager", vedi window.title) resta quello
        # nativo della title bar; il wordmark grafico è nell'intestazione delle liste.
        # self.titleBar/hBoxLayout non sono API pubbliche documentate di qfluentwidgets:
        # se in una versione futura cambiasse struttura, saltiamo semplicemente il resto.
        try:
            title_bar = self.titleBar
            insert_at = title_bar.hBoxLayout.indexOf(title_bar.titleLabel) + 1
        except AttributeError:
            return
        if insert_at <= 0:
            insert_at = 2

        search_btn = TransparentToolButton(title_bar)
        search_btn.setIcon(FIF.SEARCH)
        search_btn.setFixedSize(32, 32)
        search_btn.setToolTip(tr("search.global.tooltip"))
        search_btn.clicked.connect(self._on_global_search)
        title_bar.hBoxLayout.insertWidget(insert_at, search_btn, 0, Qt.AlignLeft | Qt.AlignVCenter)

    def _on_global_search(self) -> None:
        dialog = GlobalSearchDialog(self, self.conn)
        if dialog.exec():
            result = dialog.selected_member()
            if result is not None:
                status, member_id = result
                self.switchTo(self.pages[status])
                self.pages[status].select_member_by_id(member_id)

    # -- refresh -----------------------------------------------------
    def refresh_all(self) -> None:
        for status, page in self.pages.items():
            page.set_members(get_members(self.conn, status))
        self.stats_page.refresh()

    # -- Festività (aggiornamento in background) --------------------------
    def _start_holiday_refresh(self) -> None:
        """Il download è opzionale e non deve mai rallentare l'avvio: gira in un thread
        separato, con la sua connessione al database (sqlite3 non è condivisibile tra
        thread), e aggiorna la scheda Calendario solo se ha trovato qualcosa di nuovo."""
        self._holiday_refresh_signal = _HolidayRefreshSignal()
        self._holiday_refresh_signal.finished.connect(self._on_holidays_refreshed)
        threading.Thread(target=self._refresh_holidays_worker, daemon=True).start()

    def _refresh_holidays_worker(self) -> None:
        updated = refresh_holidays_if_needed(self.db_path)
        self._holiday_refresh_signal.finished.emit(updated)

    def _on_holidays_refreshed(self, updated: bool) -> None:
        if updated:
            self.calendar_page.refresh()

    def _on_changelog(self) -> None:
        ChangelogDialog(self).exec()

    # -- Controllo aggiornamenti -------------------------------------------
    def _start_update_check(self) -> None:
        """Un controllo veloce ad ogni avvio (una singola richiesta a GitHub, con
        timeout breve): se c'è una versione più recente lo si segnala una volta sola,
        non ad ogni riapertura del programma per la stessa versione già vista."""
        self._update_check_signal = _UpdateCheckSignal()
        self._update_check_signal.finished.connect(self._on_update_checked)
        threading.Thread(target=self._check_update_worker, daemon=True).start()

    def _check_update_worker(self) -> None:
        tag = fetch_latest_release_tag()
        self._update_check_signal.finished.emit(tag or "")

    def _on_update_checked(self, tag: str) -> None:
        if not tag or not is_newer(tag, __version__):
            return
        if get_setting(self.conn, UPDATE_NOTIFIED_SETTING) == tag:
            return
        set_setting(self.conn, UPDATE_NOTIFIED_SETTING, tag)
        box = MessageBox(tr("update.available.title"), tr("update.available.body", version=tag.lstrip("vV")), self)
        box.yesButton.setText(tr("update.available.open"))
        box.cancelButton.setText(tr("button.later"))
        if box.exec():
            QDesktopServices.openUrl(QUrl(RELEASES_PAGE_URL))

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

    def _open_nation_in_current(self, nation_display_name: str) -> None:
        """Da "Apri in Membri attuali" nel grafico nazioni: passa alla scheda Membri
        attuali e filtra con la ricerca già esistente lì, invece di costruire una
        vista/filtro dedicati per una cosa che la ricerca fa già."""
        page = self.pages[STATUS_ATTIVO]
        self.switchTo(page)
        page.search_box.setText(nation_display_name)

    # -- CRUD ----------------------------------------------------------
    def _on_add(self, status: str) -> None:
        dialog = MemberDialog(self, member=None, status=status)
        if dialog.exec():
            values = dialog.values()
            # La lista si può cambiare nel form: quella scelta là vince su quella della
            # scheda da cui si è premuto "Aggiungi", che ne è solo la preselezione.
            status = values["status"] or status
            still_on_discord = bool(values["still_on_discord"])
            member_id = add_member(
                self.conn,
                family_name=values["family_name"],
                main_name=values["main_name"],
                discord_name=values["discord_name"],
                nations=values["nations"],
                status=status,
                note=values["note"],
                data_inserimento=values["data_inserimento"],
                still_on_discord=still_on_discord,
            )
            self.refresh_all()

            new_member = Member(
                id=member_id,
                family_name=values["family_name"],
                main_name=values["main_name"],
                discord_name=values["discord_name"],
                status=status,
                data_inserimento=values["data_inserimento"],
                note=values["note"],
                nations=values["nations"],
                still_on_discord=still_on_discord,
            )
            QGuiApplication.clipboard().setText(discord_copy_text(new_member))
            self._notify(
                tr("notify.member_added.title"),
                tr("notify.member_added.body_clipboard", name=values["family_name"], status=status_label(status)),
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
                still_on_discord=values["still_on_discord"],
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
            self._backup("move")
            move_member_status(self.conn, member.id, target, note=note, still_on_discord=dialog.still_on_discord())
            self.refresh_all()
            self._notify(
                tr("notify.member_moved.title"),
                tr("notify.member_moved.body", name=member.family_name, status=status_label(target)),
            )

    # -- Backup ----------------------------------------------------------
    def _extra_backup_dir(self) -> Path | None:
        value = get_setting(self.conn, EXTRA_DIR_SETTING)
        return Path(value) if value else None

    def _backup(self, reason: str):
        return backup_database(self.db_path, reason, self._extra_backup_dir())

    def _on_backup_now(self) -> None:
        result = self._backup("manual")
        if result.path is None:
            return
        self._notify(tr("backup.notify.created.title"), tr("backup.notify.created.body", name=result.path.name))
        if result.extra_error:
            self._notify(
                tr("backup.notify.extra_failed.title"),
                tr("backup.notify.extra_failed.body", error=result.extra_error),
                error=True,
            )

    def _on_open_backups(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(backups_dir())))

    def _on_pick_extra_dir(self) -> None:
        path_str = QFileDialog.getExistingDirectory(self, tr("backup.pick_extra_dir"))
        if not path_str:
            return
        folder = Path(path_str)
        try:
            probe = folder / ".nightshade_write_test"
            probe.write_text("ok")
            probe.unlink()
        except OSError as exc:
            self._notify(tr("backup.notify.extra_bad.title"), tr("backup.notify.extra_bad.body", error=exc), error=True)
            return
        set_setting(self.conn, EXTRA_DIR_SETTING, str(folder))
        self.settings_page.set_extra_backup_dir(str(folder))
        self._notify(tr("backup.notify.extra_set.title"), tr("backup.notify.extra_set.body", path=str(folder)))

    def _on_clear_extra_dir(self) -> None:
        set_setting(self.conn, EXTRA_DIR_SETTING, "")
        self.settings_page.set_extra_backup_dir(None)
        self._notify(tr("backup.notify.extra_removed.title"), tr("backup.notify.extra_removed.body"))

    def _on_restore(self) -> None:
        extra = self._extra_backup_dir()
        dialog = RestoreBackupDialog(self, list_backups(backups_dir(), *([extra] if extra else [])))
        if not dialog.exec():
            return
        chosen = dialog.selected_backup()
        if chosen is None:
            return
        if not is_valid_backup(chosen.path):
            self._notify(tr("backup.notify.restore_failed.title"), tr("backup.restore.invalid"), error=True)
            return
        confirm = MessageBox(
            tr("backup.restore.confirm.title"),
            tr("backup.restore.confirm.body", when=format_backup_when(chosen)),
            self,
        )
        if not confirm.exec():
            return

        self.notes_page.save()
        self._backup("pre-restore")
        self.conn.close()
        try:
            restore_backup(chosen.path, self.db_path)
        except OSError as exc:
            self.conn = connect(self.db_path)
            self._notify(
                tr("backup.notify.restore_failed.title"),
                tr("backup.notify.restore_failed.body", error=exc),
                error=True,
            )
            return
        restart_app()

    # -- Import / Export / Reset ---------------------------------------
    def _on_import(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(self, tr("dialog.pick_import_file"), "", "Excel (*.xlsx)")
        if not path_str:
            return
        self.run_import(Path(path_str))

    def run_import(self, path: Path) -> None:
        """Anteprima + import di un file Excel: usato sia dal menu Impostazioni sia
        dal primo avvio (import automatico proposto se il database è vuoto), così
        entrambi i casi passano dalla stessa anteprima che segnala i doppioni invece
        di scartarli silenziosamente con la policy 'salta' di default."""
        try:
            preview = parse_workbook(path)
        except (KeyError, OSError) as exc:
            self._notify(tr("notify.import_failed.title"), tr("notify.import_failed.body", error=exc), error=True)
            return

        duplicate_count = sum(
            1 for row in preview.rows if find_duplicate(self.conn, row.family_name, row.main_name) is not None
        )
        intra_duplicates = find_intra_file_duplicates(preview.rows)

        dialog = ImportPreviewDialog(self, preview, duplicate_count, intra_duplicates)
        if not dialog.exec():
            return

        self._backup("import")
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

        self._backup("reset")
        reset_database(self.conn)
        self.refresh_all()
        self._notify(tr("notify.reset_done.title"), tr("notify.reset_done.body"))
