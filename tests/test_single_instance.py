import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QTest

from gilda_app.utils import single_instance as si


@pytest.fixture(scope="module")
def qapp():
    return QCoreApplication.instance() or QCoreApplication([])


def test_second_instance_is_refused_and_first_is_notified(qapp, tmp_path):
    db = tmp_path / "gilda.db"
    first = si.SingleInstance(db)
    second = si.SingleInstance(db)
    woken = []
    try:
        assert first.acquire() is True
        first.activation_requested.connect(lambda: woken.append(1))
        assert second.acquire() is False
        QTest.qWait(200)
        assert woken == [1]
    finally:
        first.release()
        second.release()


def test_channel_is_free_again_after_release(qapp, tmp_path):
    db = tmp_path / "gilda.db"
    first = si.SingleInstance(db)
    assert first.acquire() is True
    first.release()
    again = si.SingleInstance(db)
    try:
        assert again.acquire() is True
    finally:
        again.release()


def test_different_databases_do_not_block_each_other(qapp, tmp_path):
    a = si.SingleInstance(tmp_path / "a" / "gilda.db")
    b = si.SingleInstance(tmp_path / "b" / "gilda.db")
    try:
        assert a.acquire() is True
        assert b.acquire() is True
    finally:
        a.release()
        b.release()


def test_release_current_frees_the_registered_instance(qapp, tmp_path):
    db = tmp_path / "gilda.db"
    first = si.SingleInstance(db)
    assert first.acquire() is True
    si.release_current()
    again = si.SingleInstance(db)
    try:
        assert again.acquire() is True
    finally:
        again.release()
