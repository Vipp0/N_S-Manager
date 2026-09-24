"""Stato dei server di Black Desert (in pratica: online oppure in manutenzione) letto
dall'API di bdoalerts.net, un solo endpoint per tutte le regioni."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from gilda_app.utils.bdoalerts_api import ERROR_BAD_RESPONSE, ApiError, api_get

# Ordine con cui le regioni compaiono nella scheda. Le chiavi sono quelle dell'API
# (con il trattino, es. "console-na"); il nome mostrato è in i18n ("region.<chiave>").
REGIONS = ["eu", "na", "console-eu", "console-na", "kr", "sa", "asia"]
DEFAULT_REGION = "eu"


@dataclass
class RegionStatus:
    in_maintenance: bool
    ends_at: datetime | None = None


def _parse_datetime(value) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_status(payload: dict) -> dict[str, RegionStatus]:
    """Da {"regions": {"eu": {"in_maintenance": ..., "ends_at": ...}, ...}} a un dict per
    regione. Chiavi normalizzate con il trattino; le regioni malformate si saltano
    invece di far fallire tutto."""
    regions = payload.get("regions")
    if not isinstance(regions, dict):
        raise ApiError(ERROR_BAD_RESPONSE)
    result: dict[str, RegionStatus] = {}
    for key, info in regions.items():
        if not isinstance(info, dict) or "in_maintenance" not in info:
            continue
        result[str(key).replace("_", "-")] = RegionStatus(
            in_maintenance=bool(info["in_maintenance"]),
            ends_at=_parse_datetime(info.get("ends_at")),
        )
    if not result:
        raise ApiError(ERROR_BAD_RESPONSE)
    return result


def remaining_text(status: RegionStatus, now: datetime | None = None) -> str | None:
    """Tempo che manca alla fine della manutenzione ("2h 15m", "40m"), None se la fine
    non è nota o è già passata. Calcolato da ends_at e non dal campo time_remaining
    dell'API, il cui formato non è documentato."""
    if status.ends_at is None:
        return None
    delta = status.ends_at - (now or datetime.now(timezone.utc))
    if delta <= timedelta(0):
        return None
    minutes = int(delta.total_seconds() // 60)
    hours, minutes = divmod(minutes, 60)
    if hours >= 24:
        days, hours = divmod(hours, 24)
        return f"{days}g {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{max(minutes, 1)}m"


def fetch_server_status(api_key: str) -> dict[str, RegionStatus]:
    return parse_status(api_get("/api/maintenance-status/all", api_key))
