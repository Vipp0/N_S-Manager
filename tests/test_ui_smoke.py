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
        window.log_page,
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
    from gilda_app.ui.main_window import UPDATE_CHECK_INTERVAL_MS
    from gilda_app.utils.update_check import ReleaseInfo

    assert window._update_timer.isActive() and window._update_timer.interval() == UPDATE_CHECK_INTERVAL_MS
    offered = []
    monkeypatch.setattr(window, "_offer_update", lambda info: offered.append(info.tag))
    window.show()
    window._update_manual, window._update_periodic = False, True
    window._on_update_checked(ReleaseInfo("v99.0"))
    assert offered == []  # a programma aperto non compare una finestra che interrompe: solo una striscia
    assert window.update_strip.isVisible()
    window.update_strip.hide()
    window._on_update_checked(ReleaseInfo("v99.0"))  # la stessa versione non si segnala due volte
    assert not window.update_strip.isVisible()
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
    normal_icon = window.windowIcon().pixmap(32, 32).toImage()
    assert window.dashboard_page._greeting.isHidden()

    _mode(window, "halloween")  # prova fuori stagione
    assert window._season is not None and window._season.key == "halloween"
    assert not window.dashboard_page._greeting.isHidden() and "Halloween" in window.dashboard_page._greeting.text()
    assert window.dashboard_page._wordmark.pixmap().toImage() != normal_logo  # logo di Halloween
    assert window.pages["attivo"]._wordmark.pixmap().toImage() != normal_logo  # anche nelle liste
    assert themeColor().name() != normal_accent
    assert window.windowIcon().pixmap(32, 32).toImage() != normal_icon  # icona della finestra/barra delle applicazioni
    dashboard = window.dashboard_page
    assert not dashboard._decor.isHidden() and dashboard._decor._pixmaps  # ragnatela e ragno degli angoli
    assert not dashboard._greeting_icon.isHidden()  # zucca accanto agli auguri
    window.resize(1100, 720)
    assert not dashboard._cluster.isHidden()  # il gruppo di zucche sta sotto i riquadri, a qualunque larghezza
    dashboard._reflow(3)
    dashboard._reflow(1)
    assert not dashboard._cluster.isHidden()

    page = window.pages["attivo"]  # liste: zucca e corvo ai lati del logo, solo se la pagina è larga
    page.resize(1400, 700)
    page._update_decor_visibility()
    assert not page._decor_left.isHidden() and not page._decor_right.isHidden()
    page.resize(900, 700)
    page._update_decor_visibility()
    assert page._decor_left.isHidden() and page._decor_right.isHidden()

    for other in (window.notes_page, window.calendar_page, window.bdo_page, window.stats_page, window.settings_page):
        assert other._decor._pixmaps, other  # un ornamento per scheda

    _mode(window, "off")  # finita la festa: tutto com'era
    assert all(not p._decor._pixmaps for p in (window.notes_page, window.calendar_page, window.bdo_page,
                                                 window.stats_page, window.settings_page))
    assert window.windowIcon().pixmap(32, 32).toImage() == normal_icon
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


def test_event_log_page_lists_operations_with_colors_filter_and_search(qapp, window):
    from gilda_app.db.database import add_member, move_member_status
    from gilda_app.ui import event_log_page as elp

    member = add_member(window.conn, "Registrato", "Main", "", [], "attivo")
    move_member_status(window.conn, member, "ex_membro", note="inattivo")
    move_member_status(window.conn, member, "attivo")
    window.refresh_all()
    page = window.log_page

    labels = [page.table.item(row, elp.EVENT_COLUMN).text() for row in range(page.table.rowCount())]
    assert labels[:3] == ["Rientro", "Uscita", "Ingresso"]  # il più recente in alto
    from gilda_app.ui.chips import CHIP_TONE_ROLE, TONE_BAD, TONE_GOOD

    tones = [page.table.item(row, elp.EVENT_COLUMN).data(CHIP_TONE_ROLE) for row in range(3)]
    assert tones == [TONE_GOOD, TONE_BAD, TONE_GOOD]  # l'evento è un'etichetta verde (entra) o rossa (esce)
    assert "inattivo" in page.table.item(1, elp.DETAIL_COLUMN).text()

    page.filter_box.setCurrentIndex(page.filter_box.findData(elp.FILTER_BAD))
    assert [page.table.item(r, elp.EVENT_COLUMN).text() for r in range(page.table.rowCount())] == ["Uscita"]
    page.filter_box.setCurrentIndex(page.filter_box.findData(elp.FILTER_ALL))
    page.search_box.setText("nessuno-con-questo-nome")
    assert page.table.rowCount() == 0 and not page._empty.isHidden()
    page.search_box.setText("registrato")
    assert page.table.rowCount() == 3

    received = []
    page.member_requested.connect(received.append)
    page._on_double_click(page.table.model().index(0, 0))
    assert received == [member]


def _chips(card):
    """(testo, tono) delle etichette di un riquadro della dashboard, riga per riga."""
    from gilda_app.ui.chips import ChipLabel

    grid = card._chip_grid
    found = []
    for index in range(grid.count()):
        widget = grid.itemAt(index).widget()
        if isinstance(widget, ChipLabel):
            found.append(widget.text())
    return found


def test_dashboard_movements_and_ex_member_birthdays_carry_coloured_chips(qapp, window):
    from datetime import date

    from gilda_app.db.database import add_member, move_member_status

    today = date.today()
    add_member(window.conn, "Arrivato", "A", "", [], "attivo", data_inserimento=today.isoformat())
    gone = add_member(window.conn, "Partito", "P", "", [], "attivo", data_inserimento="2024-01-01")
    move_member_status(window.conn, gone, "ex_membro")
    banned = add_member(window.conn, "Cattivo", "C", "", [], "attivo", data_inserimento="2024-01-01")
    move_member_status(window.conn, banned, "bannato")
    add_member(window.conn, "ExFesta", "E", "", [], "ex_membro", birthday=f"1990-{today.month:02d}-{today.day:02d}")
    window.refresh_all()

    moves = window.dashboard_page._info_cards["info_joins"]
    assert moves._lines.isHidden() and not moves._chip_rows.isHidden()
    assert sorted(_chips(moves)) == ["Bannato", "Entrato", "Uscito"]  # niente più " · entrato" nel testo
    texts = [moves._chip_grid.itemAt(i).widget().text() for i in range(moves._chip_grid.count())]
    assert not any("·" in t for t in texts)

    birthdays = window.dashboard_page._info_cards["info_birthdays"]
    assert _chips(birthdays) == ["Ex membro"]  # solo per chi non è più un membro attuale

    # senza righe con etichetta il riquadro torna al testo normale
    other = window.dashboard_page._info_cards["info_anniversaries"]
    assert not other._lines.isHidden() and other._chip_rows.isHidden()


def test_chip_colours_follow_the_meaning(qapp):
    from gilda_app.ui import chips

    assert chips.chip_foreground(chips.TONE_GOOD).name() == "#15803d"
    assert chips.chip_foreground(chips.TONE_BAD).name() == "#c42b1c"
    assert chips.chip_background(chips.TONE_OUTLINE).alpha() == 0  # solo il contorno
    assert 0 < chips.chip_background(chips.TONE_GOOD).alpha() < 80  # fondo tenue, il testo resta leggibile


def test_global_search_shows_the_status_as_a_coloured_chip(qapp, window):
    from gilda_app.db.database import add_member
    from gilda_app.ui.chips import CHIP_TONE_ROLE, TONE_BAD, TONE_GOOD, TONE_WARN
    from gilda_app.ui.global_search import STATUS_COLUMN, GlobalSearchDialog

    add_member(window.conn, "Cercaattivo", "", "", [], "attivo")
    add_member(window.conn, "Cercaex", "", "", [], "ex_membro")
    add_member(window.conn, "Cercaban", "", "", [], "bannato")
    dialog = GlobalSearchDialog(window, window.conn)
    dialog.search_box.setText("cerca")
    items = {dialog.results_table.item(r, 0).text(): dialog.results_table.item(r, STATUS_COLUMN) for r in range(3)}
    assert items["Cercaattivo"].text() == "Attuale" and items["Cercaattivo"].data(CHIP_TONE_ROLE) == TONE_GOOD
    assert items["Cercaex"].text() == "Ex membro" and items["Cercaex"].data(CHIP_TONE_ROLE) == TONE_WARN
    assert items["Cercaban"].text() == "Bannato" and items["Cercaban"].data(CHIP_TONE_ROLE) == TONE_BAD
    dialog.close()


def test_opening_a_deleted_member_from_the_log_does_not_crash(qapp, window):
    from gilda_app.db.database import add_member, delete_member

    member = add_member(window.conn, "Sparito", "", "", [], "attivo")
    delete_member(window.conn, member)
    window.refresh_all()
    window._open_member_from_log(member)  # solo un avviso, nessuna eccezione
    assert window.log_page.table.item(0, 1).text() == "Eliminato"


def test_event_log_shows_recent_days_unless_show_all_or_searching(qapp, window):
    from datetime import date, timedelta

    from gilda_app.db import event_log
    from gilda_app.db.database import add_member
    from gilda_app.ui import event_log_page as elp

    add_member(window.conn, "Recentissimo", "", "", [], "attivo")
    old_day = (date.today() - timedelta(days=elp.RECENT_DAYS + 30)).isoformat()
    event_log.log_event(window.conn, "added", 99, "Antichissimo", to_status="attivo", at=f"{old_day} 10:00:00", commit=True)
    window.refresh_all()
    page = window.log_page

    names = lambda: [page.table.item(r, elp.MEMBER_COLUMN).text() for r in range(page.table.rowCount())]
    assert names() == ["Recentissimo"]
    assert not page._older_note.isHidden() and "1" in page._older_note.text()

    page.show_all.setChecked(True)  # "Mostra tutto"
    assert names() == ["Recentissimo", "Antichissimo"] and page._older_note.isHidden()
    page.show_all.setChecked(False)
    page.search_box.setText("antichissimo")  # la ricerca arriva anche agli eventi vecchi
    assert names() == ["Antichissimo"]



def test_accent_colour_defaults_to_violet_is_saved_and_yields_to_a_seasonal_theme(qapp, window):
    from qfluentwidgets import themeColor

    from gilda_app.accent import ACCENT_COLORS, ACCENT_SETTING
    from gilda_app.db.database import get_setting

    _mode(window, "off")
    assert themeColor().name() == ACCENT_COLORS["violet"]  # il predefinito
    assert window.settings_page._accent_swatches["violet"].isChecked()

    window.settings_page._accent_swatches["fuchsia"].click()  # la scelta in Impostazioni
    assert get_setting(window.conn, ACCENT_SETTING) == "fuchsia"
    assert themeColor().name() == ACCENT_COLORS["fuchsia"]

    _mode(window, "halloween")  # in festa vince il colore del tema...
    assert themeColor().name() != ACCENT_COLORS["fuchsia"]
    window.settings_page._accent_swatches["slate"].click()  # ...anche se si cambia scelta intanto
    assert themeColor().name() != ACCENT_COLORS["slate"]
    _mode(window, "off")  # ...e finita la festa torna la scelta fatta
    assert themeColor().name() == ACCENT_COLORS["slate"]

    window.settings_page.set_accent("sconosciuto")  # chiave di un'altra versione: si mostra il predefinito
    assert window.settings_page._accent_swatches["violet"].isChecked()


def test_the_saved_accent_colour_is_used_at_startup(qapp, tmp_path, monkeypatch):
    from qfluentwidgets import setThemeColor, themeColor

    from gilda_app.accent import ACCENT_COLORS, ACCENT_SETTING
    from gilda_app.db.database import connect, set_setting
    from gilda_app.ui import main_window as mw

    monkeypatch.setattr(mw, "refresh_holidays_if_needed", lambda path: False)
    monkeypatch.setattr(mw, "fetch_latest_release", lambda: None)
    db = tmp_path / "gilda.db"
    conn = connect(db)
    set_setting(conn, "season_mode", "off")
    set_setting(conn, ACCENT_SETTING, "blue")
    original = themeColor()
    win = mw.MainWindow(conn, db)
    try:
        assert themeColor().name() == ACCENT_COLORS["blue"]
        assert win.settings_page._accent_swatches["blue"].isChecked()
    finally:
        win.close()
        setThemeColor(original)


def test_christmas_theme_decorates_the_whole_program_and_reverts(qapp, window):
    from qfluentwidgets import themeColor

    normal_accent = window._default_accent.name()
    _mode(window, "off")
    normal_icon = window.windowIcon().pixmap(32, 32).toImage()

    _mode(window, "natale")  # prova fuori stagione
    assert window._season.key == "natale"
    assert themeColor().name() != normal_accent
    assert window.windowIcon().pixmap(32, 32).toImage() != normal_icon
    dashboard = window.dashboard_page
    # angoli, tre palline appese e neve
    assert {"web", "spider", "spider2", "spider3", "snow", "snow2"} <= set(dashboard._decor._pixmaps)
    assert not dashboard._greeting.isHidden() and "Feste" in dashboard._greeting.text()
    assert not dashboard._greeting_icon.isHidden()
    page = window.pages["attivo"]
    page.resize(1400, 700)
    page._update_decor_visibility()
    assert not page._decor_left.isHidden() and not page._decor_right.isHidden()  # pupazzo e renna ai lati del logo
    for other in (window.notes_page, window.calendar_page, window.bdo_page, window.log_page, window.stats_page, window.settings_page):
        assert {"snow", "snow2"} <= set(other._decor._pixmaps), other  # un po' di neve in ogni intestazione
        own = [key for key in other._decor._pixmaps if isinstance(key, tuple)]
        assert own and other._decor._pixmaps[own[0]] is not None, other  # e un ornamento proprio della scheda

    _mode(window, "off")
    assert themeColor().name() == normal_accent
    assert not dashboard._decor._pixmaps and page._decor_left.pixmap().isNull()


def test_update_strip_announces_new_version_and_can_be_closed(qapp, window, monkeypatch):
    from gilda_app.utils.update_check import ReleaseInfo

    window.show()
    assert not window.update_strip.isVisible()
    info = ReleaseInfo(tag="v9.9")
    window._announce_update(info)
    assert window.update_strip.isVisible()
    assert "9.9" in window.update_strip._text.text()
    offered = []
    monkeypatch.setattr(window, "_offer_update", offered.append)
    window.update_strip._button.click()
    assert offered == [info]
    assert window.update_strip.isVisible()  # resta finché non la si chiude
    window.update_strip._close.click()
    assert not window.update_strip.isVisible()


def test_english_interface_says_ex_members_not_former():
    from gilda_app.i18n import STRINGS

    assert STRINGS["status.ex_membro"]["en"] == "Ex members"
    assert not [key for key, texts in STRINGS.items() if "former" in texts["en"].lower() and key != "search.formerly"]


def _settle_cover(window):
    """Ferma l'animazione dei numeri (parte da sola quando la dashboard compare) e mostra i valori veri."""
    hero = window.dashboard_page._hero
    hero._animation.stop()
    hero._finish_animation()
    return hero


def test_cover_shows_members_slots_and_the_recent_counts(qapp, window):
    from gilda_app.db.database import add_member, move_member_status
    from gilda_app.ui.dashboard_cover import ZONE_ACTIVE, ZONE_BANNED, ZONE_EX

    for index in range(5):
        add_member(window.conn, f"Attivo{index}", "", "", [], "attivo", data_inserimento="2025-01-01")
    gone = add_member(window.conn, "Partito", "", "", [], "attivo")
    move_member_status(window.conn, gone, "ex_membro")
    banned = add_member(window.conn, "Cattivo", "", "", [], "attivo")
    move_member_status(window.conn, banned, "bannato")
    window.refresh_all()
    hero = _settle_cover(window)
    assert hero._numbers == {ZONE_ACTIVE: 5, ZONE_EX: 1, ZONE_BANNED: 1}
    assert "5" in hero._big.text() and "/ 100" in hero._big.text()
    assert hero._slots.text() == "95 posti liberi"
    assert hero._mini[ZONE_EX][1].text() == "1" and hero._mini[ZONE_BANNED][1].text() == "1"


def test_cover_over_the_cap_says_by_how_much_without_blocking(qapp, window):
    from gilda_app.db.database import add_member

    for index in range(5):
        add_member(window.conn, f"M{index}", "", "", [], "attivo")
    window.settings_page.capacity_spin.setValue(4)  # il tetto si cambia in Impostazioni
    hero = _settle_cover(window)
    assert hero._slots.text() == "1 oltre il tetto" and "/ 4" in hero._big.text()
    window.settings_page.capacity_spin.setValue(5)
    assert hero._slots.text() == "0 posti liberi"
    window.settings_page.capacity_spin.setValue(6)
    assert hero._slots.text() == "1 posto libero"


def test_the_guild_capacity_setting_is_saved_and_restored(qapp, window):
    from gilda_app.capacity import guild_capacity

    window.settings_page.capacity_spin.setValue(120)
    assert guild_capacity(window.conn) == 120
    window.settings_page.set_capacity(100)  # mostra il valore salvato senza riscriverlo
    assert guild_capacity(window.conn) == 120


def test_cover_zones_open_the_right_pages(qapp, window):
    from gilda_app.ui.dashboard_cover import ZONE_ACTIVE, ZONE_BANNED, ZONE_CHART, ZONE_EX
    from gilda_app.ui.dashboard_page import TILE_BDO, TILE_CALENDAR, TILE_NOTES, TILE_SETTINGS

    dash = window.dashboard_page
    opened = []
    dash.tile_clicked.connect(opened.append)
    hero = dash._hero
    hero.active_zone.clicked.emit()
    hero.chart_zone.clicked.emit()
    hero._mini  # le due zone piccole
    for zone in hero.right.findChildren(type(hero.active_zone)):
        zone.clicked.emit()
    for key in (TILE_CALENDAR, TILE_BDO, TILE_NOTES, TILE_SETTINGS):
        dash._tiles[key].clicked.emit()
    assert opened == [ZONE_ACTIVE, ZONE_CHART, ZONE_EX, ZONE_BANNED, TILE_CALENDAR, TILE_BDO, TILE_NOTES, TILE_SETTINGS]
    # e il programma le porta alla scheda giusta
    window._open_tile(ZONE_CHART)
    assert window.stackedWidget.currentWidget() is window.stats_page
    window._open_tile(ZONE_EX)
    assert window.stackedWidget.currentWidget() is window.pages["ex_membro"]


def test_cover_chart_views_and_the_note_about_unrecorded_exits(qapp, window):
    from gilda_app.ui.dashboard_cover import VIEW_TENURE, VIEW_TREND, VIEW_TURNOVER

    from gilda_app.db.database import add_member

    add_member(window.conn, "Primo", "", "", [], "attivo")
    window.conn.execute("UPDATE members SET created_at = '2026-08-01 10:00:00'")
    hero = _settle_cover(window)
    window.refresh_all()
    hero._set_view(VIEW_TURNOVER)
    assert not hero._note.isHidden() and "dal 01-08-2026" in hero._note.text()  # le uscite prima non si sanno
    assert hero.chart._view == VIEW_TURNOVER
    hero._set_view(VIEW_TREND)
    assert hero.chart._view == VIEW_TREND
    hero._set_view(VIEW_TENURE)
    assert hero.chart._view == VIEW_TENURE and hero._note.isHidden()
    for view in (VIEW_TURNOVER, VIEW_TREND, VIEW_TENURE, "nations"):  # ogni vista si disegna senza eccezioni, anche senza dati
        hero._set_view(view)
        hero.chart.resize(500, 200)
        hero.chart.grab()


def test_cover_note_is_hidden_when_the_exits_cover_the_whole_year(qapp, window):
    from gilda_app.db.database import add_member

    add_member(window.conn, "Primo", "", "", [], "attivo")
    window.conn.execute("UPDATE members SET created_at = '2020-01-01 10:00:00'")
    hero = _settle_cover(window)
    window.refresh_all()
    hero._set_view("turn")
    assert hero._note.isHidden()


def test_cover_rearranges_for_a_narrow_window(qapp, window):
    dash = window.dashboard_page
    dash._reflow_cover(1400)
    assert dash._hero._wide and dash._band_grid.columnStretch(3) == 1
    dash._reflow_cover(960)
    assert not dash._hero._wide and dash._band_grid.columnStretch(3) == 0  # sezioni su due file, grafico sotto
    assert dash._tiles["notes"].edge_top and not dash._tiles["calendar"].edge_top
    dash._reflow_cover(1400)
    assert dash._hero._wide and not dash._tiles["notes"].edge_top


def test_cover_numbers_count_up_once_and_end_on_the_real_values(qapp, window):
    from gilda_app.db.database import add_member

    for index in range(3):
        add_member(window.conn, f"M{index}", "", "", [], "attivo")
    window.refresh_all()
    dash = window.dashboard_page
    hero = dash._hero
    assert dash._intro_pending
    window.show()
    qapp.processEvents()
    assert not dash._intro_pending  # parte alla prima comparsa, una volta sola
    hero._animation.setCurrentTime(0)
    hero._render_numbers(0.0)
    assert hero._big.text().startswith("0")
    hero._animation.stop()
    hero._finish_animation()
    assert hero._big.text().startswith("3") and not hero._animating
    window.hide()
    window.show()
    qapp.processEvents()
    assert not hero._animating  # tornando sulla dashboard i numeri non rifanno l'animazione


def test_cover_greeting_lives_inside_the_cover(qapp, window):
    dash = window.dashboard_page
    assert dash._wordmark is dash._hero.wordmark and dash._greeting is dash._hero.greeting
    dash.set_greeting("Buone Feste!", "#2a6fdb")
    assert not dash._hero.greeting.isHidden() and "Feste" in dash._hero.greeting.text()
    dash.set_greeting(None)
    assert dash._hero.greeting.isHidden()


def test_cover_nations_view_shows_the_top_nations_with_their_counts(qapp, window):
    from gilda_app.db.database import add_member
    from gilda_app.ui.dashboard_cover import NATIONS_SHOWN, VIEW_NATIONS

    for nation, count in (("Italy", 3), ("Spain", 2), ("Uk", 1), ("United Kingdom", 1)):  # "Uk" e "United Kingdom" insieme
        for index in range(count):
            add_member(window.conn, f"{nation}{index}", "", "", [nation], "attivo")
    for index in range(NATIONS_SHOWN + 2):  # tante nazioni quanto basta a superare quelle mostrate
        add_member(window.conn, f"Altra{index}", "", "", [["France", "Germany", "Poland", "Portugal", "Greece", "Norway", "Japan", "Brazil"][index]], "attivo")
    window.refresh_all()
    hero = _settle_cover(window)
    chart = hero.chart
    assert [(name, count) for name, _raw, count in chart._nations[:3]] == [("Italia", 3), ("Regno Unito", 2), ("Spagna", 2)]
    hero._set_view(VIEW_NATIONS)
    assert chart._view == VIEW_NATIONS
    assert hero._legend.text().count("nazioni") == 1 and f"{len(chart._nations)} nazioni" in hero._legend.text()
    assert hero._note.isHidden()
    chart.resize(500, 220)
    chart.grab()  # si disegna senza eccezioni
    assert len(chart._nations) > NATIONS_SHOWN  # il grafico ne mostra solo le prime, il totale è nella legenda


def test_cover_nations_view_without_members_says_there_is_no_data(qapp, window):
    hero = _settle_cover(window)
    hero._set_view("nations")
    assert hero.chart._nations == []
    hero.chart.resize(500, 220)
    hero.chart.grab()
