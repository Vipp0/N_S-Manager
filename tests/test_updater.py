import hashlib
import io
import zipfile
from unittest.mock import patch

import pytest

from gilda_app.utils import update_check as uc
from gilda_app.utils import updater as up


# -- lettura della release ------------------------------------------------------
def _release(assets, body=""):
    return {"tag_name": "v2.2", "body": body, "assets": assets}


def _asset(name="Night_Shade Manager 2.2 - update.zip", **extra):
    return {"name": name, "browser_download_url": "https://example.test/" + name.replace(" ", "_"), "size": 10, **extra}


def test_parse_release_uses_asset_digest():
    info = uc.parse_release(_release([_asset(digest="sha256:" + "AB" * 32)]))
    assert info.can_install and info.sha256 == "ab" * 32 and info.asset_size == 10


def test_parse_release_falls_back_to_hash_in_notes():
    info = uc.parse_release(_release([_asset()], body="Novità\nSHA256: " + "cd" * 32))
    assert info.sha256 == "cd" * 32


def test_parse_release_without_update_zip_cannot_install():
    info = uc.parse_release(_release([_asset(name="source.zip")]))
    assert info.tag == "v2.2" and not info.can_install and info.sha256 is None


def test_parse_release_without_tag_is_none():
    assert uc.parse_release({"assets": []}) is None


# -- scaricamento ---------------------------------------------------------------
class _Response(io.BytesIO):
    def __init__(self, data):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _info(data, sha=True):
    return uc.ReleaseInfo("v2.2", "x.zip", "https://example.test/x.zip", len(data), hashlib.sha256(data).hexdigest() if sha else None)


def test_download_ok_reports_progress(tmp_path):
    data = b"x" * 600_000
    seen = []
    with patch.object(up.urllib.request, "urlopen", return_value=_Response(data)):
        up.download_release(_info(data), tmp_path / "d.zip", lambda f, _k: seen.append(f))
    assert (tmp_path / "d.zip").read_bytes() == data
    assert seen[-1] == 1.0


def test_download_wrong_checksum_rejected(tmp_path):
    data = b"abc"
    info = _info(data)
    info.sha256 = "0" * 64
    with patch.object(up.urllib.request, "urlopen", return_value=_Response(data)):
        with pytest.raises(up.UpdateError, match="checksum"):
            up.download_release(info, tmp_path / "d.zip")


def test_download_truncated_rejected(tmp_path):
    info = _info(b"abcdef", sha=False)
    with patch.object(up.urllib.request, "urlopen", return_value=_Response(b"abc")):
        with pytest.raises(up.UpdateError, match="incomplete"):
            up.download_release(info, tmp_path / "d.zip")


def test_download_network_error(tmp_path):
    with patch.object(up.urllib.request, "urlopen", side_effect=OSError("down")):
        with pytest.raises(up.UpdateError):
            up.download_release(_info(b"abc"), tmp_path / "d.zip")


# -- estrazione -----------------------------------------------------------------
def _make_zip(path, files):
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def test_extract_ok(tmp_path):
    _make_zip(tmp_path / "a.zip", {up.EXE_NAME: "exe", "_internal/lib.dll": "dll"})
    up.extract_release(tmp_path / "a.zip", tmp_path / "stage")
    assert (tmp_path / "stage" / up.EXE_NAME).read_text() == "exe"
    assert (tmp_path / "stage" / "_internal" / "lib.dll").read_text() == "dll"


def test_extract_rejects_path_escape(tmp_path):
    _make_zip(tmp_path / "a.zip", {up.EXE_NAME: "exe", "../evil.txt": "x"})
    with pytest.raises(up.UpdateError, match="unsafe"):
        up.extract_release(tmp_path / "a.zip", tmp_path / "stage")
    assert not (tmp_path / "evil.txt").exists()


def test_extract_rejects_zip_without_exe(tmp_path):
    _make_zip(tmp_path / "a.zip", {"readme.txt": "x"})
    with pytest.raises(up.UpdateError, match="package"):
        up.extract_release(tmp_path / "a.zip", tmp_path / "stage")


def test_extract_rejects_corrupt_zip(tmp_path):
    (tmp_path / "a.zip").write_bytes(b"not a zip")
    with pytest.raises(up.UpdateError):
        up.extract_release(tmp_path / "a.zip", tmp_path / "stage")


# -- sostituzione ---------------------------------------------------------------
def _app(tmp_path):
    target = tmp_path / "app"
    (target / "_internal").mkdir(parents=True)
    (target / up.EXE_NAME).write_text("old exe")
    (target / "_internal" / "lib.dll").write_text("old dll")
    (target / "_internal" / "gone.dll").write_text("only in old")
    (target / "gilda.db").write_text("DATABASE")
    (target / "backups").mkdir()
    (target / "backups" / "b.db").write_text("backup")
    stage = tmp_path / "stage"
    (stage / "_internal" / "sub").mkdir(parents=True)
    (stage / up.EXE_NAME).write_text("new exe")
    (stage / "_internal" / "lib.dll").write_text("new dll")
    (stage / "_internal" / "sub" / "extra.dll").write_text("new extra")
    return target, stage


def test_apply_replaces_program_and_keeps_user_files(tmp_path):
    target, stage = _app(tmp_path)
    seen = []
    up.apply_staged_update(stage, target, lambda f, k: seen.append((f, k)))
    assert (target / up.EXE_NAME).read_text() == "new exe"
    assert (target / "_internal" / "lib.dll").read_text() == "new dll"
    assert (target / "_internal" / "sub" / "extra.dll").read_text() == "new extra"
    assert not (target / "_internal" / "gone.dll").exists()
    assert (target / "gilda.db").read_text() == "DATABASE"
    assert (target / "backups" / "b.db").read_text() == "backup"
    assert (target / (up.EXE_NAME + ".old")).read_text() == "old exe"
    assert (target / "_internal.old" / "gone.dll").exists()
    assert seen[-1][0] == 1.0 and seen[0][1] == "update.step.backup"


def test_apply_failure_restores_old_version(tmp_path):
    target, stage = _app(tmp_path)
    real_copy = up.shutil.copy2
    calls = {"n": 0}

    def flaky(src, dst, *a, **k):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("disk full")
        return real_copy(src, dst, *a, **k)

    with patch.object(up.shutil, "copy2", side_effect=flaky):
        with pytest.raises(up.UpdateError, match="disk full"):
            up.apply_staged_update(stage, target)
    assert (target / up.EXE_NAME).read_text() == "old exe"
    assert (target / "_internal" / "lib.dll").read_text() == "old dll"
    assert (target / "_internal" / "gone.dll").exists()
    assert not (target / "_internal" / "sub").exists()
    assert (target / "gilda.db").read_text() == "DATABASE"
    assert not (target / (up.EXE_NAME + ".old")).exists()
    assert not (target / "_internal.old").exists()


def test_apply_overwrites_stale_old_copies(tmp_path):
    target, stage = _app(tmp_path)
    (target / "_internal.old").mkdir()
    (target / "_internal.old" / "stale.dll").write_text("stale")
    up.apply_staged_update(stage, target)
    assert not (target / "_internal.old" / "stale.dll").exists()
    assert (target / "_internal.old" / "gone.dll").exists()


def test_cleanup_removes_leftovers_but_not_user_files(tmp_path):
    target, stage = _app(tmp_path)
    up.apply_staged_update(stage, target)
    (target / up.UPDATE_DIR_NAME).mkdir()
    (target / "notes.old").write_text("unrelated, no base file")
    up.cleanup_leftovers(target)
    assert not (target / up.UPDATE_DIR_NAME).exists()
    assert not (target / "_internal.old").exists()
    assert not (target / (up.EXE_NAME + ".old")).exists()
    assert (target / "notes.old").exists()
    assert (target / "gilda.db").exists()


def test_wait_for_exit_returns_true_for_dead_pid():
    assert up.wait_for_exit(0) is True
