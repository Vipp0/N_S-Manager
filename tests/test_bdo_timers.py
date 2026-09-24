from datetime import datetime, timezone

import pytest

from gilda_app.utils.bdo_timers import countdown_text, parse_boss_timers, parse_reset_timers, upcoming_bosses
from gilda_app.utils.bdoalerts_api import ApiError

RESET_PAYLOAD = {
    "region": "eu",
    "daily_reset": {"next_reset": "2026-09-25T00:00:00+00:00", "countdown": "12h 55m"},
    "weekly_reset": {"next_reset": "2026-10-01T00:00:00+00:00"},
    "imperial_delivery": {"next_reset": "2026-09-24T12:00:00+00:00"},
    "day_night_cycle": {"current_cycle": "Day", "next_cycle": "Night", "next_change": "2026-09-24T11:39:00+00:00"},
}
BOSS_PAYLOAD = {
    "region": "eu",
    "bosses": [
        {"boss_name": "Garmoth", "next_spawn": "2026-09-24T14:00:00+02:00"},
        {"boss_name": "Sangoon", "next_spawn": "2026-09-24T16:00:00+02:00"},
        {"boss_name": "Karanda", "next_spawn": "2026-09-24T16:00:00+02:00"},
        {"boss_name": "Kutum", "next_spawn": "2026-09-24T19:00:00+02:00"},
        {"nonsense": True},
    ],
    "previous_boss": {"boss_names": ["Golden Pig King", "Kzarka"], "spawn_time": "2026-09-24T02:00:00+02:00"},
}


def test_parse_reset_timers():
    timers = parse_reset_timers(RESET_PAYLOAD)
    assert set(timers.resets) == {"daily_reset", "weekly_reset", "imperial_delivery"}
    assert timers.resets["daily_reset"] == datetime(2026, 9, 25, tzinfo=timezone.utc)
    assert timers.cycle == "Day"
    assert timers.cycle_change == datetime(2026, 9, 24, 11, 39, tzinfo=timezone.utc)


def test_parse_reset_timers_rejects_garbage():
    with pytest.raises(ApiError):
        parse_reset_timers({"region": "eu"})


def test_parse_boss_timers_groups_same_time():
    timers = parse_boss_timers(BOSS_PAYLOAD)
    assert [g.names for g in timers.upcoming] == [["Garmoth"], ["Sangoon", "Karanda"], ["Kutum"]]
    assert timers.previous_names == ["Golden Pig King", "Kzarka"]
    assert timers.previous_when is not None


def test_parse_boss_timers_rejects_garbage():
    with pytest.raises(ApiError):
        parse_boss_timers({"bosses": "boh"})


def test_upcoming_bosses_drops_past_ones():
    timers = parse_boss_timers(BOSS_PAYLOAD)
    now = datetime(2026, 9, 24, 14, 30, tzinfo=timezone.utc)  # le 16:30 in Italia... UTC+2: 16:30
    remaining = upcoming_bosses(timers, now)
    assert [g.names for g in remaining] == [["Kutum"]]


def test_countdown_text():
    now = datetime(2026, 9, 24, 11, 4, tzinfo=timezone.utc)
    assert countdown_text(datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc), now) == "56m"
    assert countdown_text(datetime(2026, 9, 25, 0, 0, tzinfo=timezone.utc), now) == "12h 56m"
    assert countdown_text(datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc), now) == "6g 12h"
    assert countdown_text(datetime(2026, 9, 24, 11, 0, tzinfo=timezone.utc), now) == "0m"
