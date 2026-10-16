from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest

from gilda_app.utils import bdo_notice as bn
from gilda_app.utils import maintenance_estimate as me
from gilda_app.utils.server_status import RegionStatus


def page(*blocks, extra=""):
    """Pagina nella forma degli avvisi veri: ogni blocco = (durata, [sigle], [orari])."""
    body = ""
    for duration, zones, ranges in blocks:
        body += "<p>■ Maintenance Schedule:</p>"
        body += f"<p>{duration}</p><table><tr>" + "".join(f"<th>{z}</th>" for z in zones) + "</tr>"
        body += "<tr>" + "".join(f"<td>{r}</td>" for r in ranges) + "</tr></table>"
        body += "<p>■ Maintenance Impact:</p><p>- Unable to log in.</p>"
    return f"<html><head><style>.x{{}}</style><script>var a = '01:00 - 02:00';</script></head><body>{extra}{body}</body></html>"


REGULAR = page(
    ("4 hours", ["PDT", "EDT", "UTC", "CEST"], ["01:00 - 05:00", "04:00 - 08:00", "08:00 - 12:00", "10:00 - 14:00"]),
    ("2 hours", ["PDT", "EDT", "UTC", "CEST"], ["01:00 - 03:00", "04:00 - 06:00", "08:00 - 10:00", "10:00 - 12:00"]),  # sito web
)
TEMPORARY = page(("2 hours", ["PT", "ET", "UTC", "CEST"], ["01:00 - 03:00", "04:00 - 06:00", "08:00 - 10:00", "10:00 - 12:00"]))
WINTER = page(("4 hours", ["PT", "ET", "UTC", "CET"], ["01:00 - 05:00", "04:00 - 08:00", "09:00 - 13:00", "10:00 - 14:00"]))


def utc(day, hour, minute=0, month=10):
    return datetime(2026, month, day, hour, minute, tzinfo=timezone.utc)


def test_regular_notice_uses_the_first_block_which_is_the_game():
    s = bn.parse_schedule(REGULAR, date(2026, 10, 15))
    assert (s.start, s.end) == (utc(15, 8), utc(15, 12))  # non le 2 ore del sito web


def test_temporary_notice_is_two_hours():
    s = bn.parse_schedule(TEMPORARY, date(2026, 10, 16))
    assert (s.start, s.end) == (utc(16, 8), utc(16, 10))


def test_winter_notice_reads_the_utc_column_not_the_italian_one():
    s = bn.parse_schedule(WINTER, date(2026, 1, 8))
    assert (s.start.hour, s.end.hour) == (9, 13)


def test_script_and_style_content_is_ignored():
    # l'orario finto dentro <script> non deve essere letto: la prima "Maintenance Schedule" è nel corpo
    assert bn.parse_schedule(REGULAR, date(2026, 10, 15)).start.hour == 8


def test_schedule_across_midnight_ends_the_next_day():
    html = page(("4 hours", ["PT", "UTC"], ["15:00 - 19:00", "22:00 - 02:00"]))
    s = bn.parse_schedule(html, date(2026, 10, 15))
    assert (s.start, s.end) == (utc(15, 22), utc(16, 2))


@pytest.mark.parametrize(
    "html",
    [
        "",
        "<html><body>niente qui</body></html>",
        "<p>■ Maintenance Schedule:</p><p>4 hours</p>",  # sezione senza orari
        page(("4 hours", ["PT", "ET"], ["01:00 - 05:00", "04:00 - 08:00"])),  # manca la colonna UTC
        page(("4 hours", ["PT", "UTC"], ["01:00 - 05:00"])),  # sigle e orari non corrispondono
        page(("4 hours", ["PT", "UTC"], ["01:00 - 05:00", "28:00 - 99:00"])),  # orari impossibili
    ],
)
def test_unexpected_pages_give_none_instead_of_raising(html):
    assert bn.parse_schedule(html, date(2026, 10, 15)) is None


def test_only_official_https_hosts_are_fetched():
    assert bn.is_official_url("https://www.naeu.playblackdesert.com/News/Notice/Detail?groupContentNo=1")
    assert not bn.is_official_url("http://www.naeu.playblackdesert.com/x")  # niente http
    assert not bn.is_official_url("https://evil.example.com/playblackdesert.com")
    assert not bn.is_official_url("https://playblackdesert.com.evil.net/x")
    assert not bn.is_official_url("")
    with patch.object(bn.urllib.request, "urlopen", side_effect=AssertionError("non deve scaricare")):
        assert bn.fetch_schedule("https://evil.example.com/x", date(2026, 10, 15)) is None


def test_fetch_never_raises_on_network_problems():
    with patch.object(bn.urllib.request, "urlopen", side_effect=OSError("offline")):
        assert bn.fetch_schedule("https://www.naeu.playblackdesert.com/x", date(2026, 10, 15)) is None


# -- uso nella stima ------------------------------------------------------------------
def test_official_schedule_beats_the_fallback_estimate():
    published = bn.parse_schedule(TEMPORARY, date(2026, 10, 16))
    est = me.estimate_for(date(2026, 10, 16), utc(16, 9), 1, 4, published=published)  # la stima di riserva darebbe 4 ore
    assert (est.phase, est.official, est.end) == (me.ACTIVE, True, utc(16, 10))
    assert me.estimate_for(date(2026, 10, 16), utc(16, 10), 1, 4, published=published).phase == me.OVER


def test_schedule_of_another_day_is_ignored():
    stale = bn.parse_schedule(REGULAR, date(2026, 10, 15))
    est = me.estimate_for(date(2026, 10, 22), utc(22, 9), 1, 4, published=stale)
    assert not est.official and est.end == utc(22, 12)  # ripiego: 01:00 Los Angeles + 4 ore


def test_manual_extension_still_applies_on_top_of_the_official_time():
    from datetime import timedelta

    published = bn.parse_schedule(TEMPORARY, date(2026, 10, 16))
    est = me.estimate_for(date(2026, 10, 16), utc(16, 10, 30), 1, 4, extra=timedelta(hours=1), published=published)
    assert (est.phase, est.end) == (me.ACTIVE, utc(16, 11))


def test_official_flag_reaches_the_region_status_and_its_wording():
    from gilda_app.ui.server_status_footer import describe_region

    published = bn.parse_schedule(TEMPORARY, date(2026, 10, 16))
    est = me.estimate_for(date(2026, 10, 16), utc(16, 9), 1, 4, published=published)
    status = me.apply_estimate({"eu": RegionStatus(False)}, est)["eu"]
    assert status.estimated and status.official
    official_text, color = describe_region(status)
    fallback_text, _ = describe_region(RegionStatus(True, ends_at=est.end, estimated=True))
    assert "avviso" in official_text and "stimata" in fallback_text and official_text != fallback_text


def test_announced_color_orange_for_ordinary_red_for_temporary():
    from gilda_app.ui.server_status_footer import COLOR_ANNOUNCED, COLOR_MAINTENANCE, announced_color

    assert announced_color(False) == COLOR_ANNOUNCED != COLOR_MAINTENANCE
    assert announced_color(True) == COLOR_MAINTENANCE


def test_region_parts_keep_the_big_headline_short():
    from datetime import timedelta

    from gilda_app.ui.server_status_footer import describe_region_parts

    ends = datetime.now(timezone.utc) + timedelta(hours=1, minutes=30)  # nel futuro, qualunque sia l'ora
    official = RegionStatus(True, ends_at=ends, estimated=True, official=True)
    headline, detail, _ = describe_region_parts(official)
    assert headline == "In manutenzione" and "avviso" in detail and "fine tra" in detail  # il lungo sta nel dettaglio
    assert "stimata" in describe_region_parts(RegionStatus(True, ends_at=ends, estimated=True))[1]
    real = RegionStatus(True, ends_at=ends)  # dato dall'API: nessuna etichetta, solo il tempo rimasto
    assert describe_region_parts(real)[1].startswith("fine tra")
    assert describe_region_parts(RegionStatus(True))[1] is None  # fine non nota
    assert describe_region_parts(RegionStatus(False))[1] is None and describe_region_parts(None)[1] is None
    assert len(headline) < 20
