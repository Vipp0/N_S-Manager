"""Client minimale e generico per l'API di bdoalerts.net (https://bdoalerts.net/docs/api.html).

Ogni funzione che usa l'API (stato server, in futuro boss, reset, coupon...) passa da
api_get: un solo punto dove vivono l'header con la chiave, il timeout e la traduzione
degli errori in ApiError con un "kind" fisso, così la UI mostra un messaggio sensato
senza mai dover interpretare eccezioni di rete. Solo libreria standard."""
import json
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://api.bdoalerts.net"
REQUEST_TIMEOUT_SECONDS = 6

ERROR_NO_KEY = "no_key"
ERROR_AUTH = "auth"
ERROR_RATE_LIMIT = "rate_limit"
ERROR_NOT_FOUND = "not_found"
ERROR_NETWORK = "network"
ERROR_BAD_RESPONSE = "bad_response"


class ApiError(Exception):
    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


def api_get(path: str, api_key: str, params: dict | None = None) -> dict:
    """GET su BASE_URL + path, ritorna il JSON decodificato (un dict). Solleva sempre
    e solo ApiError. La chiave viaggia solo nell'header e non compare mai in messaggi
    di errore o log."""
    if not api_key:
        raise ApiError(ERROR_NO_KEY)
    url = BASE_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url, headers={"X-API-Key": api_key, "Accept": "application/json", "User-Agent": "Night-Shade-Manager"}
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise ApiError(ERROR_AUTH) from None
        if exc.code == 429:
            raise ApiError(ERROR_RATE_LIMIT) from None
        if exc.code == 404:
            raise ApiError(ERROR_NOT_FOUND) from None
        raise ApiError(ERROR_BAD_RESPONSE) from None
    except (urllib.error.URLError, OSError):
        raise ApiError(ERROR_NETWORK) from None
    except ValueError:
        raise ApiError(ERROR_BAD_RESPONSE) from None
    if not isinstance(data, dict):
        raise ApiError(ERROR_BAD_RESPONSE)
    return data
