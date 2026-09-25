import os
import sqlite3
import threading
from datetime import date, datetime, timezone
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QFileDialog, QVBoxLayout
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
    delete_setting,
    get_setting,
    move_member_status,
    old_names_by_member,
    reset_database,
    set_setting,
    update_member,
)
from gilda_app.i18n import get_language, tr
from gilda_app.importer.excel_export import export_workbook
from gilda_app.importer.excel_import import find_intra_file_duplicates, import_row, parse_workbook
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO, Member, status_label
from gilda_app.ui.bdo_page import BdoPage, timer_summary_lines
from gilda_app.ui.calendar_page import CalendarPage
from gilda_app.ui.dashboard_page import (
    TILE_BDO,
    TILE_CALENDAR,
    TILE_NOTES,
    TILE_SETTINGS,
    TILE_STATS,
    DashboardPage,
)
from gilda_app.ui.changelog_dialog import ChangelogDialog
from gilda_app.ui.global_search import GlobalSearchDialog
from gilda_app.ui.import_dialog import ImportPreviewDialog
from gilda_app.ui.member_dialog import MemberDialog
from gilda_app.ui.member_table import MemberListPage
from gilda_app.ui.move_dialog import MoveDialog
from gilda_app.ui.notes_page import NotesPage
from gilda_app.ui.player_profile_dialog import BdoContext
from gilda_app.ui.progress_dialog import ImportProgressDialog
from gilda_app.ui.reset_dialog import ResetConfirmDialog
from gilda_app.ui.restore_dialog import RestoreBackupDialog, format_backup_when
from gilda_app.ui.server_status_footer import ServerStatusFooter, describe_error, describe_region
from gilda_app.ui.settings_page import SettingsPage
from gilda_app.ui.update_window import UpdateDownloadWorker, UpdateProgressWindow
from gilda_app.ui.stats_view import StatsPage
from gilda_app.utils.discord_format import discord_copy_text
from gilda_app.version import __version__
from gilda_app.utils.icons import ban_icon
from gilda_app.utils.paths import app_dir, backups_dir
from gilda_app.utils.bdo_guild import compare_guild, fetch_guild
from gilda_app.utils.bdo_news import fetch_news, upcoming_maintenance
from gilda_app.utils.bdo_timers import fetch_boss_timers, fetch_reset_timers
from gilda_app.utils.bdoalerts_api import ERROR_NO_KEY, ApiError
from gilda_app.utils.restart import restart_app
from gilda_app.utils.server_status import DEFAULT_REGION, fetch_server_status
from gilda_app.utils import updater
from gilda_app.utils.update_check import RELEASES_PAGE_URL, ReleaseInfo, fetch_latest_release, is_newer

STATUS_ORDER = [STATUS_ATTIVO, STATUS_EX_MEMBRO, STATUS_BANNATO]
APP_ICON_PATH = Path(__file__).resolve().parent.parent / "resources" / "app_icon.png"
UPDATE_NOTIFIED_SETTING = "update_notified_version"
API_KEY_SETTING = "bdoalerts_api_key"
SERVER_REGION_SETTING = "server_status_region"
GUILD_NAME_SETTING = "bdo_guild_name"
SERVER_STATUS_INTERVAL_MS = 5 * 60 * 1000
TIMERS_TICK_MS = 30 * 1000


class _HolidayRefreshSignal(QObject):
    """Ponte verso il thread Qt: un segnale può essere emesso da un altro thread in
    sicurezza, una chiamata diretta a un widget no."""

    finished = Signal(bool)


class _UpdateCheckSignal(QObject):
    finished = Signal(object)  # ReleaseInfo oppure None


class _ServerStatusSignal(QObject):
    # Porta al thread Qt o il dict delle regioni o il "kind" dell'errore (str).
    finished = Signal(object)


class _NewsSignal(QObject):
    finished = Signal(object)


class _TimersSignal(QObject):
    # (ResetTimers | kind, BossTimers | kind): ogni metà è i dati oppure il "kind" dell'errore.
    finished = Signal(object)


class _GuildSignal(QObject):
    finished = Signal(object)


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

        self.dashboard_page = DashboardPage(
            lambda: self.conn, self._notes_text, self._last_backup_text, self
        )
        self.dashboard_page.setObjectName("page_dashboard")
        self.dashboard_page.tile_clicked.connect(self._open_tile)
        self.dashboard_page.add_member_requested.connect(lambda: self._on_add(STATUS_ATTIVO))
        self.dashboard_page.add_event_requested.connect(lambda: self.calendar_page.add_event_today())
        self.dashboard_page.backup_requested.connect(self._on_backup_now)
        self.addSubInterface(self.dashboard_page, FIF.HOME, tr("nav.dashboard"))

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

        self.bdo_page = BdoPage(self)
        self.bdo_page.setObjectName("page_bdo")
        self.bdo_page.refresh_requested.connect(self._refresh_server_status)
        self.addSubInterface(self.bdo_page, FIF.GLOBE, tr("nav.bdo"))

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
        self.settings_page.check_update_requested.connect(lambda: self._start_update_check(manual=True))
        self.settings_page.api_key_saved.connect(self._on_api_key_saved)
        self.settings_page.server_region_changed.connect(self._on_server_region_changed)
        self.settings_page.guild_name_saved.connect(self._on_guild_name_saved)
        self.settings_page.set_extra_backup_dir(get_setting(self.conn, EXTRA_DIR_SETTING))
        self.settings_page.set_bdo_settings(
            get_setting(self.conn, API_KEY_SETTING),
            get_setting(self.conn, SERVER_REGION_SETTING, DEFAULT_REGION),
            get_setting(self.conn, GUILD_NAME_SETTING),
        )
        self.addSubInterface(self.settings_page, FIF.SETTING, tr("nav.settings"), NavigationItemPosition.BOTTOM)

        self._setup_server_status_footer()
        self.navigationInterface.setCurrentItem(self.dashboard_page.objectName())
        self.stackedWidget.currentChanged.connect(self._on_page_changed)
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
        old_names = old_names_by_member(self.conn)
        for status, page in self.pages.items():
            page.set_members(get_members(self.conn, status), old_names)
        self.stats_page.refresh()
        self.dashboard_page.refresh()
        if getattr(self, "_guild", None) is not None:
            self._update_guild_comparison()

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

    # -- Dashboard ---------------------------------------------------------------
    def _notes_text(self) -> str:
        return self.notes_page.editor.toPlainText()

    def _last_backup_text(self) -> str | None:
        extra = get_setting(self.conn, EXTRA_DIR_SETTING)
        backups = list_backups(backups_dir(), *([Path(extra)] if extra else []))
        return format_backup_when(backups[0]) if backups else None

    def _open_tile(self, key: str) -> None:
        pages = {
            TILE_STATS: self.stats_page,
            TILE_CALENDAR: self.calendar_page,
            TILE_BDO: self.bdo_page,
            TILE_NOTES: self.notes_page,
            TILE_SETTINGS: self.settings_page,
        }
        self.switchTo(pages.get(key) or self.pages[key])

    def _on_page_changed(self, _index: int) -> None:
        # Calendario, note e backup cambiano fuori da refresh_all: la dashboard si
        # aggiorna quando ci si torna, così non mostra mai dati vecchi.
        if self.stackedWidget.currentWidget() is self.dashboard_page:
            self.dashboard_page.refresh()

    # -- Stato server BDO (footer + scheda BDO) --------------------------------
    def _setup_server_status_footer(self) -> None:
        # Le pagine stanno in widgetLayout (solo lo stackedWidget): lo si affianca al
        # footer in una colonna, così la striscia sta sotto il contenuto e non sotto
        # anche la barra di navigazione. widgetLayout non è API documentata: se cambiasse
        # struttura in una versione futura, il footer semplicemente non compare.
        self._server_statuses: dict = {}
        self._server_error: str | None = ERROR_NO_KEY
        self._server_busy = False
        self._upcoming_maintenance: str | None = None
        self._server_status_signal = _ServerStatusSignal()
        self._server_status_signal.finished.connect(self._on_server_status)
        self._resets = None
        self._bosses = None
        self._timers_error: str | None = None
        self._guild = None
        self._guild_error: str | None = None
        self._guild_signal = _GuildSignal()
        self._guild_signal.finished.connect(self._on_guild)
        self._timers_signal = _TimersSignal()
        self._timers_signal.finished.connect(self._on_timers)
        self._news_signal = _NewsSignal()
        self._news_signal.finished.connect(self._on_news)
        self.server_footer = ServerStatusFooter(self)
        self.server_footer.clicked.connect(lambda: self.switchTo(self.bdo_page))
        try:
            self.widgetLayout.removeWidget(self.stackedWidget)
            column = QVBoxLayout()
            column.setContentsMargins(0, 0, 0, 0)
            column.setSpacing(0)
            column.addWidget(self.stackedWidget, 1)
            column.addWidget(self.server_footer)
            self.widgetLayout.addLayout(column)
        except AttributeError:
            self.server_footer.hide()
        self._update_server_footer()
        self._server_timer = QTimer(self)
        self._server_timer.timeout.connect(self._refresh_server_status)
        self._server_timer.start(SERVER_STATUS_INTERVAL_MS)
        # I conti alla rovescia si ricalcolano ogni mezzo minuto dagli orari già scaricati.
        self._timers_tick = QTimer(self)
        self._timers_tick.timeout.connect(self._render_timers)
        self._timers_tick.start(TIMERS_TICK_MS)
        self._refresh_server_status()

    def _server_region(self) -> str:
        return get_setting(self.conn, SERVER_REGION_SETTING, DEFAULT_REGION) or DEFAULT_REGION

    def _refresh_server_status(self) -> None:
        """Richiesta in un thread a parte (mai bloccare l'interfaccia). La chiave si
        legge qui, nel thread Qt, perché la connessione sqlite non è usabile altrove.
        Senza chiave non parte nessuna richiesta."""
        api_key = get_setting(self.conn, API_KEY_SETTING)
        if not api_key:
            self._on_server_status(ERROR_NO_KEY)
            self._on_timers((ERROR_NO_KEY, ERROR_NO_KEY))
            return
        if self._server_busy:
            return
        self._server_busy = True
        guild_name = get_setting(self.conn, GUILD_NAME_SETTING) or ""
        threading.Thread(
            target=self._server_status_worker, args=(api_key, self._server_region(), guild_name), daemon=True
        ).start()

    def _server_status_worker(self, api_key: str, region: str, guild_name: str) -> None:
        try:
            result = fetch_server_status(api_key)
        except ApiError as exc:
            result = exc.kind
        self._server_status_signal.finished.emit(result)
        # Gli avvisi sono secondari: se falliscono lo stato dei server resta com'è.
        try:
            news = fetch_news(api_key)
        except ApiError as exc:
            news = exc.kind
        self._news_signal.finished.emit(news)
        # Reset e boss: l'API accetta il nome della regione con il trattino basso.
        api_region = region.replace("-", "_")
        try:
            resets = fetch_reset_timers(api_key, api_region)
        except ApiError as exc:
            resets = exc.kind
        try:
            bosses = fetch_boss_timers(api_key, api_region)
        except ApiError as exc:
            bosses = exc.kind
        self._timers_signal.finished.emit((resets, bosses))
        if guild_name:
            try:
                guild = fetch_guild(api_key, region, guild_name)
            except ApiError as exc:
                guild = exc.kind
            self._guild_signal.finished.emit(guild)
        else:
            self._guild_signal.finished.emit("no_guild_name")

    def _on_guild(self, result) -> None:
        if isinstance(result, str):
            self._guild = None
            self._guild_error = result
        else:
            self._guild = result
            self._guild_error = None
        self._update_guild_comparison()

    def _update_guild_comparison(self) -> None:
        """Ricalcolato anche quando cambiano i membri (refresh_all), non solo quando
        arrivano dati nuovi dall'API."""
        if self._guild is not None:
            names = {
                status: [m.family_name for m in get_members(self.conn, status)] for status in STATUS_ORDER
            }
            comparison = compare_guild(self._guild.members, names)
            self.bdo_page.show_guild(
                self._guild, comparison, {status: status_label(status) for status in STATUS_ORDER}
            )
        elif self._guild_error == "no_guild_name":
            self.bdo_page.show_guild_message(tr("bdo.guild_no_name"))
        elif self._guild_error:
            self.bdo_page.show_guild_message(describe_error(self._guild_error)[0])

    def _bdo_context(self) -> BdoContext | None:
        api_key = get_setting(self.conn, API_KEY_SETTING)
        if not api_key:
            return None
        return BdoContext(
            api_key=api_key,
            region=self._server_region(),
            guild_name=get_setting(self.conn, GUILD_NAME_SETTING) or "",
            guild=self._guild,
        )

    def _on_guild_name_saved(self, name: str) -> None:
        if name:
            set_setting(self.conn, GUILD_NAME_SETTING, name)
        else:
            delete_setting(self.conn, GUILD_NAME_SETTING)
        self._refresh_server_status()

    def _on_timers(self, result) -> None:
        resets, bosses = result
        error = None
        # Un errore passeggero non cancella gli ultimi dati validi: si continua a
        # mostrare i conti alla rovescia calcolati dagli orari già in mano.
        if isinstance(resets, str):
            error = resets
        else:
            self._resets = resets
        if isinstance(bosses, str):
            error = error or bosses
        else:
            self._bosses = bosses
        if error == ERROR_NO_KEY:
            self._resets = self._bosses = None
        self._timers_error = error
        self.bdo_page.set_timer_data(self._resets, self._bosses, error)
        self._render_timers()

    def _render_timers(self) -> None:
        self.bdo_page.render_timers()
        lines = timer_summary_lines(self._resets, self._bosses, datetime.now(timezone.utc))
        if not lines and self._timers_error:
            lines = [describe_error(self._timers_error)[0]]
        self.dashboard_page.set_timers(lines)

    def _on_news(self, result) -> None:
        if isinstance(result, str):
            self.bdo_page.show_news_error(result)
            self._upcoming_maintenance = None
        else:
            self.bdo_page.show_news(result)
            upcoming = upcoming_maintenance(result, date.today())
            self._upcoming_maintenance = (
                tr("bdo.news_upcoming", date=upcoming.maintenance_date.strftime("%d-%m-%Y")) if upcoming else None
            )
        self._update_dashboard_bdo()

    def _on_server_status(self, result) -> None:
        self._server_busy = False
        if isinstance(result, str):
            self._server_error = result
            self.bdo_page.show_error(result)
            if result == ERROR_NO_KEY:
                self.bdo_page.show_news_error(result)
        else:
            self._server_error = None
            self._server_statuses = result
            self.bdo_page.show_status(result)
        self._update_server_footer()

    def _update_server_footer(self) -> None:
        region = self._server_region()
        label = tr(f"region.{region}")
        if self._server_error:
            text, color = describe_error(self._server_error)
            self.server_footer.set_state("", text, color)
        else:
            text, color = describe_region(self._server_statuses.get(region))
            self.server_footer.set_state(label, text, color)
        self._update_dashboard_bdo()

    def _update_dashboard_bdo(self) -> None:
        region = self._server_region()
        if self._server_error:
            self.dashboard_page.set_bdo("", None, [describe_error(self._server_error)[0]])
            return
        text, color = describe_region(self._server_statuses.get(region))
        lines = [tr(f"region.{region}")]
        if self._upcoming_maintenance:
            lines.append(self._upcoming_maintenance)
        self.dashboard_page.set_bdo(text, color, lines)

    def _on_api_key_saved(self, key: str) -> None:
        if key:
            set_setting(self.conn, API_KEY_SETTING, key)
        else:
            delete_setting(self.conn, API_KEY_SETTING)
            self._server_statuses = {}
        self._refresh_server_status()

    def _on_server_region_changed(self, region: str) -> None:
        set_setting(self.conn, SERVER_REGION_SETTING, region)
        self._update_server_footer()
        self._refresh_server_status()

    def _on_changelog(self) -> None:
        ChangelogDialog(self).exec()

    # -- Controllo aggiornamenti -------------------------------------------
    def _start_update_check(self, manual: bool = False) -> None:
        """Un controllo veloce ad ogni avvio (una singola richiesta a GitHub, con
        timeout breve): se c'è una versione più recente lo si segnala una volta sola,
        non ad ogni riapertura del programma per la stessa versione già vista. Il
        controllo manuale (Impostazioni) risponde sempre, anche "sei aggiornato"."""
        self._update_manual = manual
        self._update_check_signal = _UpdateCheckSignal()
        self._update_check_signal.finished.connect(self._on_update_checked)
        threading.Thread(target=self._check_update_worker, daemon=True).start()

    def _check_update_worker(self) -> None:
        self._update_check_signal.finished.emit(fetch_latest_release())

    def _on_update_checked(self, info: ReleaseInfo | None) -> None:
        manual = getattr(self, "_update_manual", False)
        if info is None:
            if manual:
                self._notify(tr("update.check.title"), tr("update.check_failed"), error=True)
            return
        if not is_newer(info.tag, __version__):
            if manual:
                self._notify(tr("update.check.title"), tr("update.none", version=__version__))
            return
        if not manual:
            if get_setting(self.conn, UPDATE_NOTIFIED_SETTING) == info.tag:
                return
            set_setting(self.conn, UPDATE_NOTIFIED_SETTING, info.tag)
        self._offer_update(info)

    def _offer_update(self, info: ReleaseInfo) -> None:
        version = info.tag.lstrip("vV")
        can_install = info.can_install and updater.can_self_update(app_dir())
        body_key = "update.available.body_install" if can_install else "update.available.body"
        box = MessageBox(tr("update.available.title"), tr(body_key, version=version), self)
        box.yesButton.setText(tr("update.available.install" if can_install else "update.available.open"))
        box.cancelButton.setText(tr("button.later"))
        if not box.exec():
            return
        if can_install:
            self._install_update(info)
        else:
            QDesktopServices.openUrl(QUrl(RELEASES_PAGE_URL))

    def _install_update(self, info: ReleaseInfo) -> None:
        """Copia di sicurezza del database, poi schermata di avanzamento mentre si scarica e
        si prepara la nuova versione; il resto lo fa la nuova versione (vedi updater.py)."""
        try:
            self._backup("pre-update")
        except OSError:
            self._update_failed(tr("update.backup_failed"))
            return
        self._update_window = UpdateProgressWindow()
        self._update_window.set_progress(0, "")
        self._update_window.show()
        self.hide()
        self._update_worker = UpdateDownloadWorker(info, app_dir())
        self._update_worker.progress.connect(lambda percent, text: self._update_window.set_progress(percent, text or None))
        self._update_worker.finished.connect(self._on_update_prepared)
        self._update_worker.start()

    def _on_update_prepared(self, error: str) -> None:
        if not error:
            try:
                updater.launch_apply(app_dir(), os.getpid(), get_language())
            except OSError as exc:
                error = str(exc)
        if error:
            self._update_window.close()
            self.show()
            self._update_failed(error)
            return
        self.conn.close()
        QApplication.quit()

    def _update_failed(self, error: str) -> None:
        box = MessageBox(tr("update.failed.title"), tr("update.failed.body", error=error), self)
        box.yesButton.setText(tr("update.available.open"))
        box.cancelButton.setText(tr("button.cancel"))
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
                birthday=values["birthday"],
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
        dialog = MemberDialog(self, member=member, conn=self.conn, bdo=self._bdo_context())
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
                record_name_changes=True,
                update_birthday=True,
                birthday=values["birthday"],
            )
            self.refresh_all()
            self._notify(
                tr("notify.member_updated.title"),
                tr("notify.member_updated.body", name=values["family_name"]),
            )
        elif dialog.history_changed:
            # Una ricostruzione dello storico scrive subito sul database anche se poi
            # il form viene chiuso con Annulla: la lista del membro può essere cambiata.
            self.refresh_all()

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
