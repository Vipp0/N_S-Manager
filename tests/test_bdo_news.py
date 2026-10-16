from datetime import date

import pytest

from gilda_app.utils.bdo_news import parse_news, upcoming_maintenance
from gilda_app.utils.bdoalerts_api import ApiError

PAYLOAD = {
    "updates": [
        {"title": "Known Issues (Last Updated: 09/23/2026 12:00 UTC)", "url": "https://x/1", "date_posted": "Sep 23, 2026 (UTC)"},
        {"title": "September 23 (Wed) Maintenance", "url": "https://x/2", "date_posted": "Sep 22, 2026 (UTC)"},
        {"title": "BLACK DESERT MASTER CLASS 2026", "url": "http://insicuro", "date_posted": "Sep 15, 2026 (UTC)"},
        {"title": "October 1 (Thu) Maintenance", "url": "https://x/3", "date_posted": "Sep 29, 2026 (UTC)"},
        {"nonsense": True},
    ]
}


def test_parse_news_flags_maintenance_and_dates():
    items = parse_news(PAYLOAD)
    assert len(items) == 4
    assert [i.is_maintenance for i in items] == [False, True, False, True]
    assert items[1].maintenance_date == date(2026, 9, 23)
    assert items[1].posted == date(2026, 9, 22)
    assert items[0].maintenance_date is None


def test_parse_news_drops_non_https_urls():
    assert parse_news(PAYLOAD)[2].url == ""


def test_upcoming_maintenance_picks_nearest_future():
    items = parse_news(PAYLOAD)
    assert upcoming_maintenance(items, date(2026, 9, 24)).maintenance_date == date(2026, 10, 1)
    assert upcoming_maintenance(items, date(2026, 10, 2)) is None


def test_maintenance_notice_across_new_year():
    payload = {"updates": [{"title": "January 2 (Thu) Maintenance", "url": "", "date_posted": "Dec 30, 2026 (UTC)"}]}
    assert parse_news(payload)[0].maintenance_date == date(2027, 1, 2)


def test_parse_news_rejects_garbage():
    with pytest.raises(ApiError):
        parse_news({"updates": "boh"})


def _title_item(title, posted="Oct 15, 2026 (UTC)"):
    return parse_news({"updates": [{"title": title, "url": "", "date_posted": posted}]})[0]


def test_temporary_maintenance_title_with_abbreviated_month_and_year():
    # titolo reale del 16 ottobre 2026: mese abbreviato, anno scritto, trattino
    item = _title_item("Oct 16, 2026 (Fri) - Temporary Maintenance")
    assert item.is_maintenance and item.is_temporary
    assert item.maintenance_date == date(2026, 10, 16)


def test_regular_maintenance_is_not_temporary_and_still_parsed():
    item = _title_item("October 15 (Thu) Maintenance", "Oct 13, 2026 (UTC)")
    assert item.is_maintenance and not item.is_temporary
    assert item.maintenance_date == date(2026, 10, 15)


@pytest.mark.parametrize(
    "title",
    ["Sept 3 (Thu) Maintenance", "Sep 3 (Thu) Maintenance", "September 3 (Thu) Maintenance", "Sep. 3rd Maintenance"],
)
def test_month_spellings_are_all_understood(title):
    assert _title_item(title, "Sep 1, 2026 (UTC)").maintenance_date == date(2026, 9, 3)


def test_year_written_in_the_title_beats_the_posted_date():
    assert _title_item("Jan 2, 2027 (Sat) - Temporary Maintenance", "Dec 30, 2026 (UTC)").maintenance_date == date(2027, 1, 2)
    # senza data di pubblicazione leggibile ma con l'anno nel titolo si ricava comunque
    assert _title_item("Oct 16, 2026 Temporary Maintenance", "boh").maintenance_date == date(2026, 10, 16)


def test_non_maintenance_titles_with_dates_are_ignored():
    item = _title_item("BLACK DESERT MASTER CLASS 2026 (Last Updated: October 15, 2026 (Thu) 15:00 UTC)")
    assert not item.is_maintenance and item.maintenance_date is None and not item.is_temporary


def test_temporary_maintenance_is_the_upcoming_one_on_its_own_day():
    items = parse_news({"updates": [
        {"title": "Oct 16, 2026 (Fri) - Temporary Maintenance", "url": "", "date_posted": "Oct 15, 2026 (UTC)"},
        {"title": "October 22 (Thu) Maintenance", "url": "", "date_posted": "Oct 20, 2026 (UTC)"},
    ]})
    assert upcoming_maintenance(items, date(2026, 10, 16)).is_temporary
    assert not upcoming_maintenance(items, date(2026, 10, 17)).is_temporary
