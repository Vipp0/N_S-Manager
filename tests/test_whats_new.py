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
