from datetime import date, datetime, timedelta, timezone

from gilda_app.utils import maintenance_estimate as me
from gilda_app.utils.server_status import RegionStatus

DAY = date(2026, 10, 8)


def utc(hour, minute=0, day=8):
    return datetime(2026, 10, day, hour, minute, tzinfo=timezone.utc)


def test_window_is_stored_in_utc_so_italian_time_follows_daylight_saving():
    start, end = me.window_for(DAY, 8, 4)
    assert (start, end) == (utc(8), utc(12))
    # 10-14 in Italia con l'ora legale (CEST = UTC+2), 9-13 con l'ora solare (CET = UTC+1)
    assert (start + timedelta(hours=2)).hour == 10 and (end + timedelta(hours=2)).hour == 14
    winter_start, _ = me.window_for(date(2026, 11, 5), 8, 4)
    assert (winter_start + timedelta(hours=1)).hour == 9


def test_phases_around_the_window():
    assert me.estimate_for(DAY, utc(7, 59)).phase == me.UPCOMING
    assert me.estimate_for(DAY, utc(8)).phase == me.ACTIVE
    assert me.estimate_for(DAY, utc(11, 59)).phase == me.ACTIVE
    assert me.estimate_for(DAY, utc(12)).phase == me.OVER
    assert me.estimate_for(None, utc(9)) is None


def test_future_day_is_upcoming_and_past_day_is_over():
    assert me.estimate_for(date(2026, 10, 15), utc(9)).phase == me.UPCOMING
    assert me.estimate_for(date(2026, 10, 1), utc(9)).phase == me.OVER


def test_extension_moves_the_end_and_can_reopen_a_window_just_over():
    assert me.estimate_for(DAY, utc(12, 30), extra=timedelta(hours=1)).phase == me.ACTIVE
    assert me.estimate_for(DAY, utc(12, 30), extra=timedelta(hours=1)).end == utc(13)
    assert me.estimate_for(DAY, utc(13, 1), extra=timedelta(hours=1)).phase == me.OVER


def test_ended_early_closes_the_window_but_not_before_it_starts():
    assert me.estimate_for(DAY, utc(10), ended_early=True).phase == me.OVER
    assert me.estimate_for(DAY, utc(7), ended_early=True).phase == me.UPCOMING


def test_adjustable_from_start_until_a_while_after_the_end():
    est = lambda now: me.estimate_for(DAY, now)
    assert not me.adjustable(est(utc(7)), utc(7))
    assert me.adjustable(est(utc(9)), utc(9))
    assert me.adjustable(est(utc(14)), utc(14))  # finita da 2 ore, ma si può ancora segnalare
    assert not me.adjustable(est(utc(15, 30)), utc(15, 30))
    assert not me.adjustable(None, utc(9))


def test_apply_marks_online_eu_and_na_only_while_active():
    api = {"eu": RegionStatus(False), "na": RegionStatus(False), "console-eu": RegionStatus(False)}
    result = me.apply_estimate(api, me.estimate_for(DAY, utc(9)))
    for region in ("eu", "na"):
        assert result[region].in_maintenance and result[region].estimated
        assert result[region].ends_at == utc(12)
    assert not result["console-eu"].in_maintenance  # altri orari: non si stima
    assert api["eu"].in_maintenance is False  # l'originale non si modifica


def test_apply_does_nothing_before_or_after_or_without_announcement():
    api = {"eu": RegionStatus(False)}
    assert me.apply_estimate(api, me.estimate_for(DAY, utc(7))) is api
    assert me.apply_estimate(api, me.estimate_for(DAY, utc(13))) is api
    assert me.apply_estimate(api, None) is api


def test_api_maintenance_always_wins_over_the_estimate():
    real_end = utc(11, 15)
    api = {"eu": RegionStatus(True, ends_at=real_end)}
    result = me.apply_estimate(api, me.estimate_for(DAY, utc(9)))
    assert result["eu"].ends_at == real_end and not result["eu"].estimated


def test_parse_config_defaults_and_clamping():
    assert me.parse_config(None, None) == (8, 4)
    assert me.parse_config("abc", "") == (8, 4)
    assert me.parse_config("9", "5") == (9, 5)
    assert me.parse_config(99, 99) == (23, 12)
    assert me.parse_config(-3, 0) == (0, 1)
