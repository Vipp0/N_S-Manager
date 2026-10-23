from datetime import date, datetime, timedelta, timezone

from gilda_app.utils import maintenance_estimate as me
from gilda_app.utils.server_status import RegionStatus

DAY = date(2026, 10, 8)


def utc(hour, minute=0, day=8):
    return datetime(2026, 10, day, hour, minute, tzinfo=timezone.utc)


def italian_hours(day, offset_hours):
    """Ora italiana di inizio e fine della manutenzione di `day` (offset 1 = CET, 2 = CEST)."""
    start, end = me.window_for(day, 1, 4)
    return (start + timedelta(hours=offset_hours)).hour, (end + timedelta(hours=offset_hours)).hour


def test_window_follows_los_angeles_time_like_the_official_notices():
    # 8 ottobre 2026 (avviso ufficiale): 01:00-05:00 PDT = 08:00-12:00 UTC = 10:00-14:00 CEST
    start, end = me.window_for(DAY, 1, 4)
    assert (start, end) == (utc(8), utc(12))
    assert italian_hours(DAY, 2) == (10, 14)
    # 8 gennaio 2026 (avviso ufficiale): 01:00-05:00 PST = 09:00-13:00 UTC = 10:00-14:00 CET
    winter_start, winter_end = me.window_for(date(2026, 1, 8), 1, 4)
    assert (winter_start.hour, winter_end.hour) == (9, 13)
    assert italian_hours(date(2026, 1, 8), 1) == (10, 14)


def test_italian_time_stays_10_14_except_in_the_weeks_when_us_and_eu_clocks_differ():
    # autunno 2026: l'Europa passa all'ora solare il 25 ottobre, gli USA il 1 novembre
    assert italian_hours(date(2026, 10, 22), 2) == (10, 14)  # entrambi ancora con l'ora legale
    assert italian_hours(date(2026, 10, 29), 1) == (9, 13)  # discrepanza: Italia CET, California ancora PDT
    assert italian_hours(date(2026, 11, 5), 1) == (10, 14)  # tornato uguale
    # primavera 2026: gli USA passano all'ora legale l'8 marzo, l'Europa il 29
    assert italian_hours(date(2026, 3, 5), 1) == (10, 14)
    assert italian_hours(date(2026, 3, 12), 1) == (9, 13)  # discrepanza di tre settimane
    assert italian_hours(date(2026, 4, 2), 2) == (10, 14)  # tornato uguale


def test_pacific_offset_changes_exactly_at_the_us_clock_changes():
    from datetime import datetime as dt

    assert me.pacific_utc_offset(dt(2026, 3, 8, 1, 59)) == timedelta(hours=-8)
    assert me.pacific_utc_offset(dt(2026, 3, 8, 3, 0)) == timedelta(hours=-7)
    assert me.pacific_utc_offset(dt(2026, 11, 1, 0, 59)) == timedelta(hours=-7)
    assert me.pacific_utc_offset(dt(2026, 11, 1, 2, 0)) == timedelta(hours=-8)
    assert me.pacific_utc_offset(dt(2027, 3, 14, 3, 0)) == timedelta(hours=-7)  # seconda domenica di marzo 2027


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
    est = me.estimate_for(DAY, utc(10, 30), ended_at=utc(10))
    assert est.phase == me.OVER and est.confirmed and est.end == utc(10)  # finita quando l'hanno segnalato
    # segnalata prima dell'inizio previsto: non vale
    assert me.estimate_for(DAY, utc(7, 30), ended_at=utc(7)).phase == me.UPCOMING
    # la fine segnalata non può essere dopo quella prevista
    assert me.estimate_for(DAY, utc(12, 30), ended_at=utc(12, 20)).end == utc(12)


def test_recently_finished_lasts_thirty_minutes_after_the_end():
    est = lambda now, **kw: me.estimate_for(DAY, now, **kw)
    assert not me.recently_finished(est(utc(11, 59)), utc(11, 59))  # ancora in corso
    assert me.recently_finished(est(utc(12, 0)), utc(12, 0))
    assert me.recently_finished(est(utc(12, 29)), utc(12, 29))
    assert not me.recently_finished(est(utc(12, 30)), utc(12, 30))  # passati i 30 minuti
    assert not me.recently_finished(None, utc(12, 5))
    assert not me.recently_finished(me.estimate_for(DAY, utc(7)), utc(7))  # non ancora iniziata


def test_marking_finished_by_hand_starts_the_thirty_minutes_from_that_moment():
    pressed = utc(10, 40)
    assert me.recently_finished(me.estimate_for(DAY, utc(11, 0), ended_at=pressed), utc(11, 0))
    assert not me.recently_finished(me.estimate_for(DAY, utc(11, 20), ended_at=pressed), utc(11, 20))


def test_extension_after_the_planned_end_reopens_it_so_no_green_banner():
    from datetime import timedelta

    # fine prevista 12:00, alle 12:10 si preme "+1 ora": di nuovo in corso fino alle 13:10
    est = me.estimate_for(DAY, utc(12, 10), extra=timedelta(hours=1, minutes=10))
    assert est.phase == me.ACTIVE and not me.recently_finished(est, utc(12, 10))


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
    assert me.parse_config(None, None) == (1, 4)
    assert me.parse_config("abc", "") == (1, 4)
    assert me.parse_config("9", "5") == (9, 5)
    assert me.parse_config(99, 99) == (23, 12)
    assert me.parse_config(-3, 0) == (0, 1)


def test_temporary_maintenance_hours_default_and_clamping():
    assert me.parse_temporary_hours(None) == 2
    assert me.parse_temporary_hours("3") == 3
    assert me.parse_temporary_hours("abc") == 2
    assert me.parse_temporary_hours(99) == 12 and me.parse_temporary_hours(0) == 1


def test_temporary_window_is_two_hours_from_the_same_start():
    # avviso ufficiale del 16 ottobre 2026: 01:00-03:00 PT = 08:00-10:00 UTC = 10:00-12:00 CEST
    est_mid = me.estimate_for(date(2026, 10, 16), utc(9, 5, day=16), 1, 2)
    assert (est_mid.phase, est_mid.start, est_mid.end) == (me.ACTIVE, utc(8, day=16), utc(10, day=16))
    assert me.estimate_for(date(2026, 10, 16), utc(10, 0, day=16), 1, 2).phase == me.OVER


# -- scelta dell'avviso da mostrare (giovedì sera con un avviso temporaneo per il giorno dopo) --------
from types import SimpleNamespace


def _item(day, temporary=False):
    return SimpleNamespace(maintenance_date=day, is_temporary=temporary, url="")


THURSDAY = _item(date(2026, 10, 22))
FRIDAY_TEMP = _item(date(2026, 10, 23), temporary=True)
CANDIDATES = [THURSDAY, FRIDAY_TEMP]  # già in ordine di data, come li dà upcoming_maintenances


def at(day, hour, minute=0):
    return datetime(2026, 10, day, hour, minute, tzinfo=timezone.utc)


def test_thursday_evening_shows_tomorrows_temporary_notice_not_the_finished_regular_one():
    # ieri sera: la manutenzione di giovedì (08-12 UTC) è finita da ore, quella temporanea del venerdì è annunciata
    assert me.pick_current(CANDIDATES, at(22, 18), 1, 4, 2) is FRIDAY_TEMP


def test_the_regular_notice_stays_while_it_is_upcoming_active_or_just_finished():
    assert me.pick_current(CANDIDATES, at(22, 7), 1, 4, 2) is THURSDAY  # non ancora iniziata
    assert me.pick_current(CANDIDATES, at(22, 10), 1, 4, 2) is THURSDAY  # in corso
    assert me.pick_current(CANDIDATES, at(22, 12, 10), 1, 4, 2) is THURSDAY  # finita da 10 minuti: serve al banner verde
    assert me.pick_current(CANDIDATES, at(22, 12, 29), 1, 4, 2) is THURSDAY
    assert me.pick_current(CANDIDATES, at(22, 12, 31), 1, 4, 2) is FRIDAY_TEMP  # passati i 30 minuti: avanti il prossimo


def test_an_extension_keeps_the_notice_current_past_the_planned_end():
    from datetime import timedelta

    adjust = lambda day: (timedelta(hours=1), None) if day == date(2026, 10, 22) else (timedelta(0), None)
    assert me.pick_current(CANDIDATES, at(22, 12, 40), 1, 4, 2, adjust_for=adjust) is THURSDAY  # fine slittata alle 13


def test_temporary_notice_uses_its_own_duration_when_deciding_if_it_is_over():
    # temporanea del venerdì 08-10 UTC: alle 10:20 è finita da 20 minuti (resta), alle 10:40 no
    assert me.pick_current([FRIDAY_TEMP], at(23, 10, 20), 1, 4, 2) is FRIDAY_TEMP
    assert me.pick_current([FRIDAY_TEMP], at(23, 10, 40), 1, 4, 2) is None
    # con la durata ordinaria (4 ore) alle 10:40 sarebbe ancora in corso: conta quella delle temporanee
    assert me.pick_current([_item(date(2026, 10, 23))], at(23, 10, 40), 1, 4, 2) is not None


def test_nothing_to_pick_when_everything_is_long_finished_or_empty():
    assert me.pick_current([THURSDAY], at(22, 20), 1, 4, 2) is None
    assert me.pick_current([], at(22, 20), 1, 4, 2) is None


def test_official_schedule_decides_when_a_notice_is_over():
    from gilda_app.utils.bdo_notice import PublishedSchedule

    short = PublishedSchedule(date(2026, 10, 22), at(22, 8), at(22, 9))  # durata vera: 1 ora
    published = lambda item: short if item is THURSDAY else None
    assert me.pick_current(CANDIDATES, at(22, 9, 40), 1, 4, 2, published_for=published) is FRIDAY_TEMP
