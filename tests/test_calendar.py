import sqlite3
from datetime import date

import pytest

from gilda_app.db.calendar_events import (
    add_event,
    delete_event,
    get_all_events,
    occurrences_in_range,
    update_event,
)
from gilda_app.db.migrations import migrate


def _row(start, unit="none", interval=1, end=None):
    return {
        "start_date": start,
        "recurrence_unit": unit,
        "recurrence_interval": interval,
        "recurrence_end_date": end,
    }


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


def test_single_event_inside_and_outside_range():
    row = _row("2026-03-10")
    assert occurrences_in_range(row, date(2026, 3, 1), date(2026, 3, 31)) == [date(2026, 3, 10)]
    assert occurrences_in_range(row, date(2026, 4, 1), date(2026, 4, 30)) == []
    assert occurrences_in_range(row, date(2026, 2, 1), date(2026, 2, 28)) == []


def test_daily_every_3_days():
    row = _row("2026-03-01", "daily", 3)
    got = occurrences_in_range(row, date(2026, 3, 1), date(2026, 3, 10))
    assert got == [date(2026, 3, 1), date(2026, 3, 4), date(2026, 3, 7), date(2026, 3, 10)]


def test_weekly_every_2_weeks_biweekly():
    row = _row("2026-03-02", "weekly", 2)  # lunedì
    got = occurrences_in_range(row, date(2026, 3, 1), date(2026, 3, 31))
    assert got == [date(2026, 3, 2), date(2026, 3, 16), date(2026, 3, 30)]


def test_weekly_series_started_long_before_range_stays_aligned():
    # serie iniziata mesi prima: le date devono restare allineate al passo originale
    row = _row("2025-01-06", "weekly", 2)
    got = occurrences_in_range(row, date(2026, 3, 1), date(2026, 3, 31))
    assert got  # ci sono occorrenze nel mese
    for d in got:
        assert (d - date(2025, 1, 6)).days % 14 == 0
        assert date(2026, 3, 1) <= d <= date(2026, 3, 31)


def test_monthly_clamps_day_to_end_of_short_months():
    row = _row("2026-01-31", "monthly", 1)
    got = occurrences_in_range(row, date(2026, 1, 1), date(2026, 4, 30))
    assert got == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)]


def test_recurrence_end_date_is_respected_inclusive():
    row = _row("2026-03-02", "weekly", 1, end="2026-03-16")
    got = occurrences_in_range(row, date(2026, 3, 1), date(2026, 3, 31))
    assert got == [date(2026, 3, 2), date(2026, 3, 9), date(2026, 3, 16)]


def test_series_starting_after_range_has_no_occurrences():
    row = _row("2026-06-01", "daily", 1)
    assert occurrences_in_range(row, date(2026, 3, 1), date(2026, 3, 31)) == []


def test_crud_roundtrip(conn):
    event_id = add_event(conn, "2026-03-10", "Khan", "#ff0000", note="Boss", recurrence_unit="weekly", recurrence_interval=2)
    rows = get_all_events(conn)
    assert len(rows) == 1
    assert rows[0]["title"] == "Khan"
    assert rows[0]["recurrence_interval"] == 2

    update_event(conn, event_id, "2026-03-11", "Khan 2", "#00ff00", recurrence_unit="none")
    updated = get_all_events(conn)[0]
    assert (updated["start_date"], updated["title"], updated["color"], updated["recurrence_unit"]) == (
        "2026-03-11",
        "Khan 2",
        "#00ff00",
        "none",
    )

    delete_event(conn, event_id)
    assert get_all_events(conn) == []
