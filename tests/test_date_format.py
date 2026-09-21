from gilda_app.utils.date_format import iso_month_to_display, iso_to_display


def test_iso_to_display_date_only():
    assert iso_to_display("2025-03-07") == "07-03-2025"


def test_iso_to_display_ignores_time_part():
    assert iso_to_display("2025-03-07 10:20:00") == "07-03-2025"


def test_iso_month_to_display():
    assert iso_month_to_display("2025-03") == "03-2025"
