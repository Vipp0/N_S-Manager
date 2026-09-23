"""Controllo se su GitHub è già disponibile una versione più recente di quella
installata. Solo un avviso con il link alla pagina di scaricamento: nessun download
o installazione automatica, quelli restano sempre una scelta manuale dell'utente."""
import json
import urllib.error
import urllib.request

RELEASES_API_URL = "https://api.github.com/repos/Vipp0/N_S-Manager/releases/latest"
RELEASES_PAGE_URL = "https://github.com/Vipp0/N_S-Manager/releases/latest"
FETCH_TIMEOUT_SECONDS = 4


def _parse_version(text: str) -> tuple[int, ...]:
    """"v1.10.2" -> (1, 10, 2). Un confronto testuale semplice sbaglierebbe (es. "1.9.0"
    sembrerebbe più recente di "1.10.0"), quindi si confrontano i numeri, non le stringhe."""
    parts = []
    for chunk in text.strip().lstrip("vV").split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_newer(remote_version: str, current_version: str) -> bool:
    return _parse_version(remote_version) > _parse_version(current_version)


def fetch_latest_release_tag() -> str | None:
    """Tag dell'ultima release pubblicata su GitHub (es. "v1.8.0"). None se non è
    raggiungibile o non esiste ancora nessuna release: il chiamante tratta None come
    "nessuna informazione disponibile", mai come un errore da mostrare all'utente."""
    request = urllib.request.Request(
        RELEASES_API_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Night-Shade-Manager"},
    )
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, ValueError):
        return None
    tag = data.get("tag_name") if isinstance(data, dict) else None
    return tag if isinstance(tag, str) and tag else None
