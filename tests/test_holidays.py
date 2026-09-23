import sqlite3
from datetime import date, timedelta

import pytest

from gilda_app.db import holidays as hol
from gilda_app.db.database import connect, get_setting


SAMPLE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260101
DTEND;VALUE=DATE:20260102
SUMMARY:New Year's Day
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260216
DTEND;VALUE=DATE:20260217
SUMMARY:Seollal (Lunar New Year)
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260505
SUMMARY:Children's Day
  continued on next line
END:VEVENT
END:VCALENDAR
"""


def test_parse_ics_holidays_extracts_date_and_name():
    events = hol.parse_ics_holidays(SAMPLE_ICS)
    assert (date(2026, 1, 1), "New Year's Day") in events
    assert (date(2026, 2, 16), "Seollal (Lunar New Year)") in events
    assert len(events) == 3


def test_parse_ics_holidays_unfolds_continuation_lines():
    events = hol.parse_ics_holidays(SAMPLE_ICS)
    title = next(name for d, name in events if d == date(2026, 5, 5))
    assert title == "Children's Day continued on next line"


def test_parse_ics_holidays_ignores_malformed_events():
    text = "BEGIN:VEVENT\nSUMMARY:No date\nEND:VEVENT\n"
    assert hol.parse_ics_holidays(text) == []


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "gilda.db"
    conn = connect(path)
    return path, conn


def test_store_and_get_holidays_in_range(db):
    path, conn = db
    hol.store_holidays(conn, [(date(2026, 1, 1), "A"), (date(2026, 5, 5), "B"), (date(2026, 12, 25), "C")])
    result = hol.get_holidays_in_range(conn, date(2026, 1, 1), date(2026, 6, 1))
    assert result == {date(2026, 1, 1): ["A"], date(2026, 5, 5): ["B"]}


def test_store_holidays_replaces_previous_content(db):
    path, conn = db
    hol.store_holidays(conn, [(date(2026, 1, 1), "old")])
    hol.store_holidays(conn, [(date(2026, 1, 1), "new")])
    result = hol.get_holidays_in_range(conn, date(2026, 1, 1), date(2026, 1, 1))
    assert result == {date(2026, 1, 1): ["new"]}


def test_should_refresh_true_when_never_done(db):
    path, conn = db
    assert hol._should_refresh(conn) is True


def test_should_refresh_false_right_after_refresh(db):
    path, conn = db
    from gilda_app.db.database import set_setting
    set_setting(conn, hol.LAST_REFRESH_SETTING, date.today().isoformat())
    assert hol._should_refresh(conn) is False


def test_should_refresh_true_after_threshold(db):
    path, conn = db
    from gilda_app.db.database import set_setting
    old = date.today() - timedelta(days=hol.REFRESH_EVERY_DAYS + 1)
    set_setting(conn, hol.LAST_REFRESH_SETTING, old.isoformat())
    assert hol._should_refresh(conn) is True


def test_refresh_holidays_if_needed_stores_fetched_data(db, monkeypatch):
    path, conn = db
    monkeypatch.setattr(hol, "fetch_holidays", lambda: [(date(2026, 1, 1), "Fetched")])
    updated = hol.refresh_holidays_if_needed(path)
    assert updated is True
    check = connect(path)
    assert hol.get_holidays_in_range(check, date(2026, 1, 1), date(2026, 1, 1)) == {date(2026, 1, 1): ["Fetched"]}
    assert get_setting(check, hol.LAST_REFRESH_SETTING) == date.today().isoformat()


def test_refresh_holidays_if_needed_skips_when_recent(db, monkeypatch):
    path, conn = db
    from gilda_app.db.database import set_setting
    set_setting(conn, hol.LAST_REFRESH_SETTING, date.today().isoformat())
    called = []
    monkeypatch.setattr(hol, "fetch_holidays", lambda: called.append(1) or [])
    updated = hol.refresh_holidays_if_needed(path)
    assert updated is False
    assert called == []


def test_refresh_holidays_if_needed_survives_network_failure(db, monkeypatch):
    path, conn = db
    def boom():
        raise OSError("no network")
    monkeypatch.setattr(hol, "fetch_holidays", boom)
    updated = hol.refresh_holidays_if_needed(path)
    assert updated is False
