import pytest

from gilda_app import whats_new as wn
from gilda_app.whats_new import Highlight, latest_release, releases_to_show


@pytest.fixture(autouse=True)
def three_releases(monkeypatch):
    item = [Highlight("COPY", "t", "x")]
    monkeypatch.setattr(wn, "WHATS_NEW", {"2.6": item, "2.7": item, "2.8": item, "2.10": item})


def test_fresh_install_without_data_shows_nothing():
    assert releases_to_show(None, "2.7", has_data=False) == []


def test_first_run_of_the_feature_on_an_existing_database_shows_only_the_latest_release():
    assert releases_to_show(None, "2.7", has_data=True) == ["2.7"]
    # versione di mezzo (patch) senza voce propria: vale l'ultima release uscita fino ad allora
    assert releases_to_show(None, "2.7.3", has_data=True) == ["2.7"]


def test_normal_update_shows_the_new_release_once_the_memory_is_updated():
    assert releases_to_show("2.6", "2.7", has_data=True) == ["2.7"]
    assert releases_to_show("2.7", "2.7", has_data=True) == []  # già visto


def test_skipping_versions_shows_every_missed_release_newest_first_up_to_three():
    assert releases_to_show("2.6", "2.8", has_data=True) == ["2.8", "2.7"]
    assert releases_to_show("2.5", "2.10", has_data=True) == ["2.10", "2.8", "2.7"]  # tetto di 3; 2.10 > 2.9 (confronto numerico)


def test_intermediate_unpublished_versions_never_show_the_popup():
    assert releases_to_show("2.6", "2.6.4", has_data=True) == []
    assert releases_to_show("2.5.4", "2.5.5", has_data=True) == []


def test_going_back_to_an_older_version_shows_nothing():
    assert releases_to_show("2.8", "2.6", has_data=True) == []


def test_releases_newer_than_the_running_version_are_ignored():
    assert releases_to_show(None, "2.5.4", has_data=True) == []
    assert releases_to_show("2.5", "2.6", has_data=True) == ["2.6"]


def test_latest_release_for_the_manual_button():
    assert latest_release("2.7.2") == "2.7"
    assert latest_release("2.10") == "2.10"
    assert latest_release("2.5.4") is None


def test_real_highlights_are_well_formed():

    # il vero elenco (non quello finto della fixture) deve avere voci complete
    import importlib

    importlib.reload(wn)
    for release, items in wn.WHATS_NEW.items():
        assert items, release
        for item in items:
            assert item.title.strip() and item.text.strip()


def test_real_release_history_selection(monkeypatch):
    import importlib

    importlib.reload(wn)  # i dati veri, non quelli della fixture
    from gilda_app.whats_new import releases_to_show as rts

    assert "2.7" in wn.WHATS_NEW and "2.6" in wn.WHATS_NEW
    assert rts("2.6", "2.7", True) == ["2.7"]  # chi aveva la 2.6 (già vista) vede solo la 2.7
    assert rts("2.6.5", "2.7", True) == ["2.7"]  # anche chi ha provato le versioni intermedie
    assert rts("2.6.3", "2.7", True) == ["2.7"]
    assert rts("2.7", "2.7", True) == []  # già vista: niente al secondo avvio
    assert rts(None, "2.7", True) == ["2.7"]  # primo avvio con la funzione su un database con dati
    assert rts(None, "2.7", False) == []  # installazione nuova
    assert rts("2.5", "2.7", True) == ["2.7", "2.6"]  # chi salta una versione vede anche quella saltata


def test_real_history_with_the_2_7_x_patches(monkeypatch):
    import importlib

    importlib.reload(wn)
    from gilda_app.whats_new import releases_to_show as rts

    assert rts("2.7", "2.7.2", True) == ["2.7.2", "2.7.1"]  # chi ha la 2.7 vede la correzione e le novità
    assert rts("2.7.1", "2.7.2", True) == ["2.7.2"]  # chi aveva già la 2.7.1 non rivede la sua correzione
    assert rts("2.7.2", "2.7.2", True) == []
    assert rts("2.6", "2.7.2", True) == ["2.7.2", "2.7.1", "2.7"]  # salto di versione: al massimo le ultime tre
    assert rts("2.6.5", "2.7.2", True) == ["2.7.2", "2.7.1", "2.7"]
    assert rts(None, "2.7.2", True) == ["2.7.2"]


def test_every_real_highlight_is_translated_and_localized_picks_the_language():
    import importlib

    importlib.reload(wn)
    for release, items in wn.WHATS_NEW.items():
        for item in items:
            assert item.title_en.strip() and item.text_en.strip(), (release, item.title)  # niente scheda solo italiana
            assert item.localized("en") == (item.title_en, item.text_en)
            assert item.localized("it") == (item.title, item.text)
    untranslated = wn.Highlight("INFO", "titolo", "testo")
    assert untranslated.localized("en") == ("titolo", "testo")  # senza traduzione, ripiego sull'italiano


def test_popup_stays_in_italian_even_if_the_program_is_in_english():
    from gilda_app import i18n

    assert wn.POPUP_LANGUAGE == "it"
    previous = i18n.get_language()
    try:
        i18n.set_language("en")
        assert i18n.tr("whatsnew.close") == "Got it"  # il programma è in inglese...
        assert i18n.tr_in(wn.POPUP_LANGUAGE, "whatsnew.close") == "Ho capito"  # ...ma il popup no
        assert i18n.tr_in("en", "whatsnew.title", version="2.7.2") == "What's new in version 2.7.2"
        assert i18n.tr_in("it", "chiave.inesistente") == "chiave.inesistente"
    finally:
        i18n.set_language(previous)


def test_real_history_for_2_7_3(monkeypatch):
    import importlib

    importlib.reload(wn)
    from gilda_app.whats_new import releases_to_show as rts

    assert rts("2.7.2", "2.7.3", True) == ["2.7.3"]
    assert rts("2.7", "2.7.3", True) == ["2.7.3", "2.7.2", "2.7.1"]  # al massimo le ultime tre
    assert rts("2.7.3", "2.7.3", True) == []
    assert len(wn.WHATS_NEW["2.7.3"]) == 3
