import sqlite3
from datetime import date

import pytest

from gilda_app.db.database import add_member, get_members, update_member
from gilda_app.db.migrations import migrate
from gilda_app.db.stats import upcoming_birthdays
from gilda_app.utils.birthday import build_birthday, next_birthday, split_birthday


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


def test_build_birthday():
    assert build_birthday(0, 0, "") is None
    assert build_birthday(5, 3, "") == "03-05"
    assert build_birthday(5, 3, "1990") == "1990-03-05"
    assert build_birthday(29, 2, "") == "02-29"
    for bad in [(5, 0, ""), (0, 3, ""), (31, 4, ""), (29, 2, "2023"), (5, 3, "90"), (5, 3, "1800"), (0, 0, "1990")]:
        with pytest.raises(ValueError):
            build_birthday(*bad)


def test_split_and_next_birthday():
    assert split_birthday("03-05") == (5, 3, None)
    assert split_birthday("1990-03-05") == (5, 3, 1990)
    assert split_birthday("boh") is None and split_birthday(None) is None
    today = date(2026, 9, 24)
    assert next_birthday("09-24", today) == (date(2026, 9, 24), None)  # oggi
    assert next_birthday("1990-01-10", today) == (date(2027, 1, 10), 37)
    assert next_birthday("02-29", date(2027, 2, 1)) == (date(2027, 2, 28), None)


def test_birthday_saved_and_not_wiped_by_import_update(conn):
    member_id = add_member(conn, "Rossi", "", "", [], "attivo", birthday="1990-03-05")
    assert get_members(conn, "attivo")[0].birthday == "1990-03-05"
    update_member(conn, member_id, "Rossi", "", "", [])  # come l'import: non tocca il compleanno
    assert get_members(conn, "attivo")[0].birthday == "1990-03-05"
    update_member(conn, member_id, "Rossi", "", "", [], update_birthday=True, birthday=None)
    assert get_members(conn, "attivo")[0].birthday is None


def test_upcoming_birthdays(conn):
    add_member(conn, "Oggi", "O", "", [], "attivo", birthday="09-24")
    add_member(conn, "Presto", "P", "", [], "attivo", birthday="1995-09-30")
    add_member(conn, "Lontano", "L", "", [], "attivo", birthday="1995-12-30")
    add_member(conn, "Ex", "E", "", [], "ex_membro", birthday="09-25")
    add_member(conn, "Senza", "S", "", [], "attivo")
    result = upcoming_birthdays(conn, date(2026, 9, 24), days=14)
    assert result == [(date(2026, 9, 24), "Oggi", "O", None), (date(2026, 9, 30), "Presto", "P", 31)]
