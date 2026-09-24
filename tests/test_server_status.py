import io
import json
import urllib.error
from datetime import datetime, timedelta, timezone

import pytest

from gilda_app.utils import bdoalerts_api
from gilda_app.utils.bdoalerts_api import ApiError, api_get
from gilda_app.utils.server_status import RegionStatus, fetch_server_status, parse_status, remaining_text

ONLINE_PAYLOAD = {
    "timestamp": "2026-01-01T00:00:00+00:00",
    "regions": {
        "eu": {"in_maintenance": False, "started_at": None, "ends_at": None, "time_remaining": None},
        "console-na": {"in_maintenance": False, "started_at": None, "ends_at": None, "time_remaining": None},
    },
}


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _patch_urlopen(monkeypatch, payload=None, error=None, captured=None):
    def fake(request, timeout=None):
        if captured is not None:
            captured["headers"] = dict(request.header_items())
            captured["url"] = request.full_url
        if error is not None:
            raise error
        return _FakeResponse(payload if isinstance(payload, bytes) else json.dumps(payload).encode())

    monkeypatch.setattr(bdoalerts_api.urllib.request, "urlopen", fake)


def test_parse_status_online():
    statuses = parse_status(ONLINE_PAYLOAD)
    assert statuses["eu"].in_maintenance is False
    assert "console-na" in statuses


def test_parse_status_maintenance_with_end():
    payload = {"regions": {"eu": {"in_maintenance": True, "ends_at": "2026-01-01T10:00:00+00:00"}}}
    status = parse_status(payload)["eu"]
    assert status.in_maintenance is True
    assert status.ends_at == datetime(2026, 1, 1, 10, tzinfo=timezone.utc)


def test_parse_status_rejects_garbage():
    with pytest.raises(ApiError):
        parse_status({"regions": "boh"})
    with pytest.raises(ApiError):
        parse_status({})


def test_remaining_text():
    now = datetime(2026, 1, 1, 8, tzinfo=timezone.utc)
    assert remaining_text(RegionStatus(True, now + timedelta(hours=2, minutes=15)), now) == "2h 15m"
    assert remaining_text(RegionStatus(True, now + timedelta(minutes=40)), now) == "40m"
    assert remaining_text(RegionStatus(True, now - timedelta(minutes=1)), now) is None
    assert remaining_text(RegionStatus(True, None), now) is None


def test_api_get_sends_key_header(monkeypatch):
    captured = {}
    _patch_urlopen(monkeypatch, ONLINE_PAYLOAD, captured=captured)
    api_get("/api/x", "chiave-finta", {"region": "eu"})
    assert captured["headers"]["X-api-key"] == "chiave-finta"
    assert captured["url"].endswith("/api/x?region=eu")


def test_api_get_without_key_makes_no_request(monkeypatch):
    _patch_urlopen(monkeypatch, error=AssertionError("non deve fare richieste"))
    with pytest.raises(ApiError) as exc:
        api_get("/api/x", "")
    assert exc.value.kind == "no_key"


@pytest.mark.parametrize(
    "error, kind",
    [
        (urllib.error.HTTPError("u", 403, "forbidden", {}, None), "auth"),
        (urllib.error.HTTPError("u", 429, "slow", {}, None), "rate_limit"),
        (urllib.error.HTTPError("u", 500, "boom", {}, None), "bad_response"),
        (urllib.error.URLError("offline"), "network"),
    ],
)
def test_api_get_errors(monkeypatch, error, kind):
    _patch_urlopen(monkeypatch, error=error)
    with pytest.raises(ApiError) as exc:
        api_get("/api/x", "k")
    assert exc.value.kind == kind


def test_api_get_bad_json(monkeypatch):
    _patch_urlopen(monkeypatch, payload=b"<html>")
    with pytest.raises(ApiError) as exc:
        api_get("/api/x", "k")
    assert exc.value.kind == "bad_response"


def test_fetch_server_status(monkeypatch):
    _patch_urlopen(monkeypatch, ONLINE_PAYLOAD)
    assert "eu" in fetch_server_status("k")
