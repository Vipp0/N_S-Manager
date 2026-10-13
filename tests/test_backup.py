import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from gilda_app.db import backup as bk
from gilda_app.db.database import connect, set_setting


@pytest.fixture
def env(tmp_path, monkeypatch):
    backups = tmp_path / "backups"
    backups.mkdir()
    monkeypatch.setattr(bk, "backups_dir", lambda: backups)
    db = tmp_path / "gilda.db"
    conn = connect(db)
    conn.execute("INSERT INTO members (family_name, main_name, discord_name, status) VALUES ('A','a','d','attivo')")
    conn.commit()
    return {"db": db, "conn": conn, "backups": backups, "tmp": tmp_path}


def _fake_backup(directory: Path, when: datetime, reason: str) -> Path:
    path = directory / f"gilda_{when.strftime('%Y%m%d_%H%M%S')}_{reason}.db"
    path.write_bytes(b"x")
    return path


def test_backup_creates_named_copy(env):
    result = bk.backup_database(env["db"], "manual")
    assert result.path.parent == env["backups"]
    assert result.path.name.endswith("_manual.db")
    assert result.extra_error is None
    assert bk.is_valid_backup(result.path)


def test_backup_mirrors_to_extra_dir(env):
    extra = env["tmp"] / "other_disk" / "nested"
    result = bk.backup_database(env["db"], "manual", extra)
    assert (extra / result.path.name).exists()
    assert result.extra_error is None


def test_backup_reports_extra_dir_failure_but_keeps_main_copy(env):
    blocker = env["tmp"] / "file_not_dir"
    blocker.write_text("x")
    result = bk.backup_database(env["db"], "manual", blocker / "sub")
    assert result.path.exists()
    assert result.extra_error


def test_list_backups_sorted_and_deduplicated(env):
    extra = env["tmp"] / "extra"
    extra.mkdir()
    now = datetime(2026, 5, 10, 12, 0, 0)
    _fake_backup(env["backups"], now - timedelta(days=2), "auto")
    newest = _fake_backup(env["backups"], now, "move")
    _fake_backup(extra, now, "move")
    (env["backups"] / "not_a_backup.db").write_bytes(b"x")
    infos = bk.list_backups(env["backups"], extra)
    assert [i.reason for i in infos] == ["move", "auto"]
    assert infos[0].path == newest


def test_daily_backup_once_per_day(env):
    first = bk.daily_backup_if_needed(env["db"])
    assert first is not None and first.path.name.endswith("_auto.db")
    assert bk.daily_backup_if_needed(env["db"]) is None


def test_daily_backup_uses_extra_dir_from_settings(env):
    extra = env["tmp"] / "extra"
    set_setting(env["conn"], bk.EXTRA_DIR_SETTING, str(extra))
    result = bk.daily_backup_if_needed(env["db"])
    assert (extra / result.path.name).exists()


def test_daily_backup_skipped_without_database(tmp_path, monkeypatch):
    monkeypatch.setattr(bk, "backups_dir", lambda: tmp_path)
    assert bk.daily_backup_if_needed(tmp_path / "missing.db") is None


def test_prune_keeps_only_latest_auto_backups(env):
    base = datetime(2026, 1, 1, 8, 0, 0)
    for i in range(5):
        _fake_backup(env["backups"], base + timedelta(days=i), "auto")
    manual = _fake_backup(env["backups"], base, "manual")
    bk.prune_auto_backups(env["backups"], keep=2)
    remaining = bk.list_backups(env["backups"])
    assert [i.reason for i in remaining].count("auto") == 2
    assert manual.exists()


def test_restore_replaces_database_content(env):
    snapshot = bk.backup_database(env["db"], "manual").path
    env["conn"].execute("DELETE FROM members")
    env["conn"].commit()
    env["conn"].close()
    bk.restore_backup(snapshot, env["db"])
    check = sqlite3.connect(env["db"])
    assert check.execute("SELECT COUNT(*) FROM members").fetchone()[0] == 1
    check.close()
    assert not env["db"].with_name("gilda.db.restoring").exists()


def test_invalid_backup_is_rejected(tmp_path):
    bad = tmp_path / "gilda_20260101_000000_manual.db"
    bad.write_bytes(b"not a database")
    assert not bk.is_valid_backup(bad)


def test_backup_with_connection_uses_online_copy_and_includes_uncommitted_free_state(env):
    env["conn"].execute("INSERT INTO members (family_name, main_name, discord_name, status) VALUES ('B','b','d','attivo')")
    env["conn"].commit()
    result = bk.backup_database(env["db"], "auto", conn=env["conn"])
    assert result.path.name.endswith("_auto.db") and bk.is_valid_backup(result.path)
    copy = sqlite3.connect(str(result.path))
    try:
        assert copy.execute("SELECT COUNT(*) FROM members").fetchone()[0] == 2
    finally:
        copy.close()


def test_nightly_backup_due_after_the_2am_boundary_only_once_per_night():
    at = lambda d, h, m=0: datetime(2026, 10, d, h, m)
    # ultima copia ieri alle 9: alle 01:59 non è ancora ora, alle 02:00 sì
    assert not bk.nightly_backup_due(at(14, 1, 59), at(13, 9))
    assert bk.nightly_backup_due(at(14, 2, 0), at(13, 9))
    # fatta alle 02:05, non si rifà per tutto il giorno e la sera
    assert not bk.nightly_backup_due(at(14, 2, 6), at(14, 2, 5))
    assert not bk.nightly_backup_due(at(14, 23, 0), at(14, 2, 5))
    # la notte dopo tocca di nuovo
    assert bk.nightly_backup_due(at(15, 2, 0), at(14, 2, 5))


def test_nightly_backup_is_skipped_when_the_startup_backup_is_recent_enough():
    at = lambda d, h, m=0: datetime(2026, 10, d, h, m)
    # PC acceso lunedì alle 9 (copia dell'avvio): la notte di martedì serve, quella di lunedì no
    assert not bk.nightly_backup_due(at(12, 15), at(12, 9))
    assert bk.nightly_backup_due(at(13, 2, 0), at(12, 9))


def test_nightly_backup_catches_up_after_a_late_wakeup():
    at = lambda d, h, m=0: datetime(2026, 10, d, h, m)
    # PC in sospensione alle 02:00, di nuovo attivo alle 07:30: la copia si fa subito
    assert bk.nightly_backup_due(at(14, 7, 30), at(13, 9))


def test_nightly_backup_due_without_any_previous_auto_backup():
    assert bk.nightly_backup_due(datetime(2026, 10, 14, 15, 0), None)


def test_latest_auto_backup_time_ignores_other_kinds(env):
    now = datetime(2026, 10, 14, 12, 0, 0)
    _fake_backup(env["backups"], now - timedelta(days=3), "auto")
    _fake_backup(env["backups"], now - timedelta(days=1), "auto")
    _fake_backup(env["backups"], now, "move")
    assert bk.latest_auto_backup_time(env["backups"]) == now - timedelta(days=1)
    assert bk.latest_auto_backup_time(env["tmp"] / "empty") is None
