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
