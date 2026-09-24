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
