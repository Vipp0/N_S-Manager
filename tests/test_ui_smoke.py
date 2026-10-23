"""Prova di avvio dell'interfaccia: costruisce la finestra vera (senza schermo) e apre ogni scheda e
i dialoghi principali. Non controlla l'aspetto: serve a scoprire subito errori da "non si apre
nemmeno" (una importazione dimenticata, un nome sbagliato) che gli altri test, che non toccano i
widget, non vedono."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    from gilda_app.db.database import connect
    from gilda_app.ui import main_window as mw

    # Niente rete: né le festività né il controllo aggiornamenti devono partire durante il test.
    monkeypatch.setattr(mw, "refresh_holidays_if_needed", lambda path: False)
    monkeypatch.setattr(mw, "fetch_latest_release", lambda: None)
    db = tmp_path / "gilda.db"
    from qfluentwidgets import setThemeColor, themeColor

    original_accent = themeColor()  # il colore d'accento è globale: va rimesso com'era dopo ogni prova
    win = mw.MainWindow(connect(db), db)
    yield win
    win.close()
    setThemeColor(original_accent)


def test_main_window_builds_and_every_page_opens(qapp, window):
    pages = [
        window.dashboard_page,
        window.calendar_page,
        window.notes_page,
        window.bdo_page,
        window.stats_page,
        window.settings_page,
        *window.pages.values(),
    ]
    window.show()
    for page in pages:
        window.switchTo(page)
        qapp.processEvents()
        assert page.isVisible()


def test_main_dialogs_build(qapp, window):
    from gilda_app.ui.calendar_event_dialog import CalendarEventDialog
    from gilda_app.ui.changelog_dialog import ChangelogDialog
    from gilda_app.ui.member_dialog import MemberDialog
    from gilda_app.ui.whats_new_dialog import WhatsNewDialog
    from gilda_app.whats_new import WHATS_NEW

    window.show()
    MemberDialog(window, member=None, status="attivo", find_duplicates=lambda name, exclude: [])
    CalendarEventDialog(window)
    ChangelogDialog(window)
    WhatsNewDialog(window, [max(WHATS_NEW, key=lambda v: tuple(int(p) for p in v.split(".")))])


def test_bdo_page_maintenance_block_shows_and_hides(qapp, window):
    page = window.bdo_page
    page.set_maintenance_info("Manutenzione · oggi, 10:00 – 14:00", "#d9730d", "", "Fonte: prova")
    assert not page._info_box.isHidden() and page._reason_frame.isHidden()  # niente motivo: solo il titolo
    page.set_maintenance_info("Manutenzione temporanea · oggi, 10:00 – 12:00", "#c42b1c", "Riga uno\nRiga due", "Fonte: prova")
    assert not page._reason_frame.isHidden() and page._reason.text() == "Riga uno\nRiga due"
    page.set_maintenance_info(None, "", "", "")
    assert page._info_box.isHidden()


def test_dashboard_stacks_maintenance_banners(qapp, window):
    dash = window.dashboard_page
    dash.set_maintenance_banner("primo", "#c42b1c")
    dash.set_extra_maintenance_banners([("secondo", "#d9730d"), ("terzo", "#c42b1c")])
    shown = [b for b in [dash._maintenance_banner, *dash._extra_banners] if not b.isHidden()]
    assert len(shown) == 3
    dash.set_extra_maintenance_banners([])
    assert [b for b in dash._extra_banners if not b.isHidden()] == []
    dash.set_maintenance_banner(None)
    assert dash._maintenance_banner.isHidden()


def test_update_check_repeats_while_the_program_stays_open(qapp, window, monkeypatch):
    from qfluentwidgets import InfoBar

    from gilda_app.ui.main_window import UPDATE_CHECK_INTERVAL_MS
    from gilda_app.utils.update_check import ReleaseInfo

    assert window._update_timer.isActive() and window._update_timer.interval() == UPDATE_CHECK_INTERVAL_MS
    offered = []
    monkeypatch.setattr(window, "_offer_update", lambda info: offered.append(info.tag))
    window.show()
    window._update_manual, window._update_periodic = False, True
    window._on_update_checked(ReleaseInfo("v99.0"))
    assert offered == []  # a programma aperto non compare una finestra che interrompe: solo una striscia
    bars = window.findChildren(InfoBar)
    assert len(bars) == 1
    window._on_update_checked(ReleaseInfo("v99.0"))  # la stessa versione non si segnala due volte
    assert len(window.findChildren(InfoBar)) == 1
    # il controllo all'avvio resta quello di prima: finestra di proposta
    window._update_manual, window._update_periodic = False, False
    window._on_update_checked(ReleaseInfo("v99.1"))
    assert offered == ["v99.1"]


def test_midnight_moves_the_calendar_to_the_new_day_and_rechecks_holidays(qapp, window, monkeypatch):
    from datetime import date, timedelta

    from PySide6.QtCore import QDate

    calls = []
    monkeypatch.setattr(window, "_start_holiday_refresh", lambda: calls.append(1))
    yesterday = date.today() - timedelta(days=1)
    window._current_day = yesterday
    window.calendar_page.calendar.setSelectedDate(QDate(yesterday.year, yesterday.month, yesterday.day))
    window._check_day_change()
    selected = window.calendar_page.calendar.selectedDate()
    assert selected == QDate.currentDate()  # si era sul giorno finito: passa a oggi
    assert calls == [1]
    # chi aveva scelto un altro giorno a mano lo ritrova com'era
    other = date.today() + timedelta(days=3)
    window._current_day = yesterday
    window.calendar_page.calendar.setSelectedDate(QDate(other.year, other.month, other.day))
    window._check_day_change()
    assert window.calendar_page.calendar.selectedDate() == QDate(other.year, other.month, other.day)


def _mode(window, mode):
    from gilda_app.db.database import set_setting

    set_setting(window.conn, "season_mode", mode)
    window.apply_season()


def test_seasonal_theme_changes_logo_greeting_and_accent_and_restores_them(qapp, window):
    from qfluentwidgets import themeColor

    normal_accent = window._default_accent.name()
    _mode(window, "off")
    normal_logo = window.dashboard_page._wordmark.pixmap().toImage()
    assert window.dashboard_page._greeting.isHidden()

    _mode(window, "halloween")  # prova fuori stagione
    assert window._season is not None and window._season.key == "halloween"
    assert not window.dashboard_page._greeting.isHidden() and "Halloween" in window.dashboard_page._greeting.text()
    assert window.dashboard_page._wordmark.pixmap().toImage() != normal_logo  # logo di Halloween
    assert window.pages["attivo"]._wordmark.pixmap().toImage() != normal_logo  # anche nelle liste
    assert themeColor().name() != normal_accent
    dashboard = window.dashboard_page
    assert not dashboard._decor.isHidden() and dashboard._decor._pixmaps  # ragnatela e ragno degli angoli
    assert not dashboard._greeting_icon.isHidden()  # zucca accanto agli auguri
    window.resize(1100, 720)
    dashboard._reflow(3)  # 5 schede informative su 3 colonne: resta una cella libera per il gruppo di zucche
    assert not dashboard._cluster.isHidden()
    dashboard._reflow(1)  # su una colonna non c'è nessun vuoto
    assert dashboard._cluster.isHidden()

    page = window.pages["attivo"]  # liste: zucca e corvo ai lati del logo, solo se la pagina è larga
    page.resize(1400, 700)
    page._update_decor_visibility()
    assert not page._decor_left.isHidden() and not page._decor_right.isHidden()
    page.resize(900, 700)
    page._update_decor_visibility()
    assert page._decor_left.isHidden() and page._decor_right.isHidden()

    _mode(window, "off")  # finita la festa: tutto com'era
    assert page._decor_left.pixmap().isNull() and page._decor_right.pixmap().isNull()
    assert window._season is None and window.dashboard_page._greeting.isHidden()
    assert dashboard._decor.isHidden() and dashboard._cluster.isHidden() and dashboard._greeting_icon.isHidden()
    assert window.dashboard_page._wordmark.pixmap().toImage() == normal_logo
    assert themeColor().name() == normal_accent


def test_midnight_checks_whether_a_theme_starts_or_ends(qapp, window, monkeypatch):
    from datetime import date, timedelta

    _mode(window, "auto")
    calls = []
    monkeypatch.setattr(window, "apply_season", lambda force=False: calls.append(1))
    monkeypatch.setattr(window, "_start_holiday_refresh", lambda: None)
    window._current_day = date.today() - timedelta(days=1)
    window._check_day_change()
    assert calls == [1]


def test_season_choice_is_remembered_and_shown_in_settings(qapp, window):
    window.settings_page.season_combo.setCurrentIndex(window.settings_page.season_combo.findData("halloween"))
    assert window._season is not None and window._season.key == "halloween"
    from gilda_app.db.database import get_setting

    assert get_setting(window.conn, "season_mode") == "halloween"
    window.settings_page.set_season_mode("off")  # caricare il valore salvato non deve cambiare niente
    assert window._season is not None


def test_seasonal_splash_and_startup_helper(qapp, tmp_path):
    from gilda_app import main as app_main
    from gilda_app.db.database import connect, set_setting
    from gilda_app.seasons import SEASONS

    db = tmp_path / "gilda.db"
    conn = connect(db)
    set_setting(conn, "season_mode", "halloween")
    conn.close()
    splash = app_main._start_seasonal_splash(db)
    assert splash is not None and splash.pixmap().width() == 720
    splash.set_dots(2)
    splash.close()
    conn = connect(db)
    set_setting(conn, "season_mode", "off")
    conn.close()
    assert app_main._start_seasonal_splash(db) is None  # tema spento: resta la schermata normale
    assert app_main._start_seasonal_splash(tmp_path / "nuovo.db") is None or SEASONS[0].contains(__import__("datetime").date.today())
