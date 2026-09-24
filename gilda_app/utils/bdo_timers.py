"""Timer di Black Desert da bdoalerts.net: reset giornaliero/settimanale, consegna
imperiale, ciclo giorno/notte e prossimi boss. L'API restituisce orari assoluti; i
conti alla rovescia si calcolano qui a partire da quelli, così restano esatti anche tra
un aggiornamento e l'altro (la risposta cattura solo l'istante della richiesta)."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from gilda_app.utils.bdoalerts_api import ERROR_BAD_RESPONSE, ApiError, api_get

# Chiavi della risposta di /api/reset-timers che hanno un "next_reset", nell'ordine
# in cui si mostrano. Il nome mostrato è in i18n ("timer.<chiave>").
RESET_KEYS = [
    "daily_reset",
    "weekly_reset",
    "imperial_delivery",
    "trade_reset",
    "barter_reset",
    "blackshrine_reset",
]
BOSS_ROWS_LIMIT = 8


@dataclass
class ResetTimers:
    resets: dict[str, datetime] = field(default_factory=dict)
    # Ciclo giorno/notte: ciclo attuale ("Day"/"Night") e istante del prossimo cambio.
    cycle: str | None = None
    cycle_change: datetime | None = None


@dataclass
class BossGroup:
    names: list[str]
    when: datetime


@dataclass
class BossTimers:
    upcoming: list[BossGroup] = field(default_factory=list)
    previous_names: list[str] = field(default_factory=list)
    previous_when: datetime | None = None


def _dt(value) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_reset_timers(payload: dict) -> ResetTimers:
    result = ResetTimers()
    for key in RESET_KEYS:
        entry = payload.get(key)
        when = _dt(entry.get("next_reset")) if isinstance(entry, dict) else None
        if when is not None:
            result.resets[key] = when
    cycle = payload.get("day_night_cycle")
    if isinstance(cycle, dict):
        result.cycle_change = _dt(cycle.get("next_change"))
        current = cycle.get("current_cycle")
        result.cycle = current if isinstance(current, str) else None
    if not result.resets and result.cycle_change is None:
        raise ApiError(ERROR_BAD_RESPONSE)
    return result


def parse_boss_timers(payload: dict) -> BossTimers:
    bosses = payload.get("bosses")
    if not isinstance(bosses, list):
        raise ApiError(ERROR_BAD_RESPONSE)
    result = BossTimers()
    for raw in bosses:
        if not isinstance(raw, dict) or not isinstance(raw.get("boss_name"), str):
            continue
        when = _dt(raw.get("next_spawn"))
        if when is None:
            continue
        # Boss con lo stesso orario di comparsa stanno insieme in una riga sola.
        if result.upcoming and result.upcoming[-1].when == when:
            result.upcoming[-1].names.append(raw["boss_name"])
        else:
            result.upcoming.append(BossGroup([raw["boss_name"]], when))
    previous = payload.get("previous_boss")
    if isinstance(previous, dict):
        names = previous.get("boss_names")
        result.previous_names = [n for n in names if isinstance(n, str)] if isinstance(names, list) else []
        result.previous_when = _dt(previous.get("spawn_time"))
    return result


def countdown_text(target: datetime, now: datetime | None = None) -> str:
    """"55m", "12h 55m", "6d 12h". Con l'orario già passato: "ora"."""
    delta = target - (now or datetime.now(timezone.utc))
    if delta <= timedelta(0):
        return "0m"
    minutes = int(delta.total_seconds() // 60)
    hours, minutes = divmod(minutes, 60)
    if hours >= 24:
        days, hours = divmod(hours, 24)
        return f"{days}g {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{max(minutes, 1)}m"


def upcoming_bosses(timers: BossTimers, now: datetime | None = None, limit: int = BOSS_ROWS_LIMIT) -> list[BossGroup]:
    """Solo i boss non ancora comparsi: tra un aggiornamento e l'altro qualcuno può
    essere già passato."""
    now = now or datetime.now(timezone.utc)
    return [group for group in timers.upcoming if group.when > now][:limit]


def fetch_reset_timers(api_key: str, region: str) -> ResetTimers:
    return parse_reset_timers(api_get("/api/reset-timers", api_key, {"region": region}))


def fetch_boss_timers(api_key: str, region: str) -> BossTimers:
    return parse_boss_timers(api_get(f"/api/boss-timers/{region}", api_key))
