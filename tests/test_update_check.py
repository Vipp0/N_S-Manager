import json
from unittest.mock import patch

from gilda_app.utils import update_check as uc


def test_parse_version_basic():
    assert uc._parse_version("v1.7.1") == (1, 7, 1)
    assert uc._parse_version("1.7.1") == (1, 7, 1)


def test_is_newer_true():
    assert uc.is_newer("v1.8.0", "1.7.1") is True


def test_is_newer_false_when_equal():
    assert uc.is_newer("v1.7.1", "1.7.1") is False


def test_is_newer_false_when_older():
    assert uc.is_newer("v1.6.0", "1.7.1") is False


def test_is_newer_numeric_not_lexicographic():
    # "1.9.0" non deve sembrare piu' recente di "1.10.0" come stringa
    assert uc.is_newer("v1.10.0", "1.9.0") is True
    assert uc.is_newer("v1.9.0", "1.10.0") is False


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_fetch_latest_release_tag_success():
    payload = json.dumps({"tag_name": "v1.8.0"}).encode("utf-8")
    with patch.object(uc.urllib.request, "urlopen", return_value=_FakeResponse(payload)):
        assert uc.fetch_latest_release_tag() == "v1.8.0"


def test_fetch_latest_release_tag_network_failure_returns_none():
    with patch.object(uc.urllib.request, "urlopen", side_effect=OSError("no network")):
        assert uc.fetch_latest_release_tag() is None


def test_fetch_latest_release_tag_malformed_json_returns_none():
    with patch.object(uc.urllib.request, "urlopen", return_value=_FakeResponse(b"not json")):
        assert uc.fetch_latest_release_tag() is None


def test_fetch_latest_release_tag_missing_tag_name_returns_none():
    payload = json.dumps({"message": "Not Found"}).encode("utf-8")
    with patch.object(uc.urllib.request, "urlopen", return_value=_FakeResponse(payload)):
        assert uc.fetch_latest_release_tag() is None


def test_is_newer_treats_missing_patch_as_zero():
    assert not uc.is_newer("v2.1", "2.1.0")
    assert not uc.is_newer("2.1.0", "2.1")
    assert uc.is_newer("v2.1", "2.0.5")
    assert uc.is_newer("2.1.1", "2.1")
