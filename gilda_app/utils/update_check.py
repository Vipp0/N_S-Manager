"""Controllo se su GitHub è già disponibile una versione più recente di quella
installata, con i dati per scaricarla (vedi updater.py). Nulla viene scaricato o
installato senza che l'utente lo scelga."""
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

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
    """Le versioni delle release possono omettere il terzo numero quando è 0 ("2.1" =
    "2.1.0"): si allineano a tre numeri prima di confrontare."""
    def padded(text: str) -> tuple[int, ...]:
        parts = _parse_version(text)
        return parts + (0,) * (3 - len(parts))

    return padded(remote_version) > padded(current_version)


@dataclass
class ReleaseInfo:
    tag: str
    asset_name: str | None = None
    asset_url: str | None = None
    asset_size: int | None = None
    sha256: str | None = None  # None se la release non lo pubblica

    @property
    def can_install(self) -> bool:
        return bool(self.asset_url)


def _fetch_release_data() -> dict | None:
    request = urllib.request.Request(
        RELEASES_API_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Night-Shade-Manager"},
    )
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def parse_release(data: dict) -> ReleaseInfo | None:
    """Estrae tag e zip di aggiornamento da una release GitHub. L'hash SHA256 viene dal
    campo "digest" dell'asset (lo calcola GitHub) oppure, in mancanza, da una riga
    "SHA256: ..." nelle note della release."""
    tag = data.get("tag_name")
    if not isinstance(tag, str) or not tag:
        return None
    assets = [
        a for a in data.get("assets") or [] if isinstance(a, dict) and str(a.get("name", "")).lower().endswith(".zip")
    ]
    asset = next((a for a in assets if "update" in a["name"].lower()), None)
    if asset is None or not isinstance(asset.get("browser_download_url"), str):
        return ReleaseInfo(tag)
    sha = None
    digest = asset.get("digest")
    if isinstance(digest, str) and digest.lower().startswith("sha256:"):
        sha = digest.split(":", 1)[1].strip().lower()
    else:
        match = re.search(r"sha-?256\D{0,12}([0-9a-fA-F]{64})", str(data.get("body") or ""), re.IGNORECASE)
        if match:
            sha = match.group(1).lower()
    size = asset.get("size")
    return ReleaseInfo(tag, asset["name"], asset["browser_download_url"], size if isinstance(size, int) else None, sha)


def fetch_latest_release() -> ReleaseInfo | None:
    """Ultima release pubblicata, con i dati dello zip. None se GitHub non è
    raggiungibile o non c'è nessuna release."""
    data = _fetch_release_data()
    return parse_release(data) if data else None


def fetch_latest_release_tag() -> str | None:
    """Tag dell'ultima release pubblicata su GitHub (es. "v1.8.0"). None se non è
    raggiungibile o non esiste ancora nessuna release: il chiamante tratta None come
    "nessuna informazione disponibile", mai come un errore da mostrare all'utente."""
    data = _fetch_release_data()
    tag = data.get("tag_name") if data else None
    return tag if isinstance(tag, str) and tag else None
