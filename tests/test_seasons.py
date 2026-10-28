from datetime import date

import pytest

from gilda_app import seasons
from gilda_app.db.database import connect, set_setting

HALLOWEEN = next(s for s in seasons.SEASONS if s.key == "halloween")
NATALE = next(s for s in seasons.SEASONS if s.key == "natale")


@pytest.fixture
def assets(tmp_path, monkeypatch):
    """Cartella di immagini finte: serve a decidere quali temi hanno i file (e quindi sono accesi)."""
    monkeypatch.setattr(seasons, "RESOURCES", tmp_path)

    def add(*keys):
        for key in keys:
            (tmp_path / f"splash_{key}.png").write_bytes(b"x")
            (tmp_path / f"wordmark_{key}.png").write_bytes(b"x")

    return add


def test_halloween_runs_from_21_october_to_2_november_inclusive():
    assert not HALLOWEEN.contains(date(2026, 10, 20))
    assert HALLOWEEN.contains(date(2026, 10, 21)) and HALLOWEEN.contains(date(2026, 10, 31))
    assert HALLOWEEN.contains(date(2026, 11, 2))
    assert not HALLOWEEN.contains(date(2026, 11, 3))


def test_halloween_greeting_only_on_31_october_and_1_november():
    assert not HALLOWEEN.greets(date(2026, 10, 30)) and HALLOWEEN.greets(date(2026, 10, 31))
    assert HALLOWEEN.greets(date(2026, 11, 1)) and not HALLOWEEN.greets(date(2026, 11, 2))
    assert not NATALE.greets(date(2026, 12, 7)) and NATALE.greets(date(2026, 12, 25))  # senza date: tutto il periodo


def test_forced_preview_always_shows_the_greeting():
    assert not seasons.greeting_active(HALLOWEEN, date(2026, 10, 25))
    assert seasons.greeting_active(HALLOWEEN, date(2026, 10, 31))
    assert seasons.greeting_active(HALLOWEEN, date(2026, 6, 15), "halloween")


def test_christmas_runs_from_8_december_to_6_january_across_the_new_year():
    assert not NATALE.contains(date(2026, 12, 7))
    assert NATALE.contains(date(2026, 12, 8)) and NATALE.contains(date(2026, 12, 31))
    assert NATALE.contains(date(2027, 1, 1)) and NATALE.contains(date(2027, 1, 6))
    assert not NATALE.contains(date(2027, 1, 7)) and not NATALE.contains(date(2026, 7, 1))


def test_a_theme_without_its_images_stays_off(assets):
    assert seasons.active_season(date(2026, 10, 25)) is None  # nessun file: normale
    assets("halloween")
    assert seasons.active_season(date(2026, 10, 25)) is HALLOWEEN
    assert seasons.active_season(date(2026, 12, 25)) is None  # Natale non ha ancora le immagini
    assets("natale")
    assert seasons.active_season(date(2026, 12, 25)) is NATALE


def test_a_theme_needs_both_images(assets, tmp_path):
    (tmp_path / "splash_halloween.png").write_bytes(b"x")  # manca il logo
    assert seasons.active_season(date(2026, 10, 25)) is None


def test_off_mode_always_gives_the_normal_look(assets):
    assets("halloween")
    assert seasons.active_season(date(2026, 10, 25), seasons.MODE_OFF) is None


def test_forced_mode_previews_a_theme_out_of_season_only_if_it_is_ready(assets):
    assets("halloween")
    assert seasons.active_season(date(2026, 6, 15), "halloween") is HALLOWEEN
    assert seasons.active_season(date(2026, 6, 15), "natale") is None  # senza immagini
    assert seasons.active_season(date(2026, 6, 15), "mai_esistito") is None


def test_selectable_modes_list_only_ready_themes(assets):
    assert seasons.selectable_modes() == ["auto", "off"]
    assets("halloween")
    assert seasons.selectable_modes() == ["auto", "off", "halloween"]


def test_read_setting_works_before_the_database_is_opened(tmp_path):
    db = tmp_path / "gilda.db"
    assert seasons.read_setting(db, "season_mode", "auto") == "auto"  # nessun database ancora
    conn = connect(db)
    set_setting(conn, "season_mode", "off")
    conn.close()
    assert seasons.read_setting(db, "season_mode", "auto") == "off"
    assert seasons.read_setting(db, "assente", "predefinito") == "predefinito"
    broken = tmp_path / "rotto.db"
    broken.write_bytes(b"questo non e' un database")
    assert seasons.read_setting(broken, "season_mode", "auto") == "auto"  # nessuna eccezione


def test_real_halloween_decorations_exist_and_are_transparent():
    from PySide6.QtGui import QImage

    for name in ("web", "spider", "cluster", "icon", "header_left", "header_right", "page_a", "page_b", "page_c"):  # i nomi che la dashboard cerca
        path = HALLOWEEN.decor_path(name)
        assert path.exists(), name
        assert QImage(str(path)).hasAlphaChannel()
    assert not HALLOWEEN.decor_path("inesistente").exists()
    assert HALLOWEEN.icon_path.exists()  # icona del programma nel periodo


def test_real_christmas_theme_is_ready_and_complete():
    from PySide6.QtGui import QImage

    assert NATALE.available and NATALE.accent and NATALE.icon_path.exists()
    assert (QImage(str(NATALE.splash_path)).width(), QImage(str(NATALE.splash_path)).height()) == (720, 540)
    assert QImage(str(NATALE.wordmark_path)).hasAlphaChannel()
    for name in ("web", "spider", "cluster", "icon", "header_left", "header_right", "page_a", "page_b", "page_c", "snow", "snow2"):
        path = NATALE.decor_path(name)
        assert path.exists() and QImage(str(path)).hasAlphaChannel(), name
    assert QImage(str(NATALE.icon_path)).hasAlphaChannel()  # sfondo trasparente, non nero


def test_christmas_greeting_runs_from_24_december_to_1_january():
    assert not NATALE.greets(date(2026, 12, 23)) and NATALE.greets(date(2026, 12, 24))
    assert NATALE.greets(date(2026, 12, 31)) and NATALE.greets(date(2027, 1, 1))
    assert not NATALE.greets(date(2027, 1, 2))
    assert seasons.greeting_active(NATALE, date(2026, 12, 10), "natale")  # nella prova si vede sempre


def test_real_halloween_images_are_the_expected_size():
    from PySide6.QtGui import QImage

    assert HALLOWEEN.available
    splash, wordmark = QImage(str(HALLOWEEN.splash_path)), QImage(str(HALLOWEEN.wordmark_path))
    assert (splash.width(), splash.height()) == (720, 540)  # come splash.png
    assert wordmark.hasAlphaChannel() and wordmark.height() == 220  # logo trasparente come wordmark.png
