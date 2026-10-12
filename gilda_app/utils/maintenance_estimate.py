"""Stima dell'orario della manutenzione, per quando l'API dice "online" a server spenti.

bdoalerts.net segnala la manutenzione solo quando se ne accorge (spesso mai), mentre gli
avvisi ufficiali danno la data ma non l'ora. Gli orari reali sono però quasi sempre gli stessi
(l'avviso ufficiale li scrive in più fusi: 08:00-12:00 UTC, cioè 10:00-14:00 in Italia d'estate):
nel giorno di una manutenzione annunciata, dentro quella finestra, se l'API dice online lo
stato mostrato è "in manutenzione (stimata)". Se l'API dice invece manutenzione, vale l'API.

L'orario è salvato in UTC e non in ora locale: l'ora legale sposta l'ora italiana ma non la
manutenzione (a fine ottobre il 10-14 diventa 9-13)."""
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone

from gilda_app.utils.server_status import RegionStatus

DEFAULT_START_HOUR_UTC = 8
DEFAULT_DURATION_HOURS = 4
MIN_DURATION_HOURS = 1
MAX_DURATION_HOURS = 12
# Gli avvisi letti (NA/EU PC) valgono per queste regioni; console, Corea, ecc. hanno altri orari.
ESTIMATED_REGIONS = ("eu", "na")
# Dopo la fine prevista si può ancora segnalare "è durata di più" per un po'.
GRACE_AFTER_END = timedelta(hours=3)

UPCOMING = "upcoming"
ACTIVE = "active"
OVER = "over"


@dataclass(frozen=True)
class Estimate:
    phase: str  # UPCOMING | ACTIVE | OVER
    start: datetime  # UTC
    end: datetime  # UTC, già comprensivo di eventuali proroghe


def parse_config(start_hour, duration_hours) -> tuple[int, int]:
    """(ora di inizio UTC, durata in ore) da valori salvati, con i valori di default se
    mancano o sono illeggibili."""
    try:
        start = int(start_hour)
    except (TypeError, ValueError):
        start = DEFAULT_START_HOUR_UTC
    try:
        hours = int(duration_hours)
    except (TypeError, ValueError):
        hours = DEFAULT_DURATION_HOURS
    return max(0, min(23, start)), max(MIN_DURATION_HOURS, min(MAX_DURATION_HOURS, hours))


def window_for(day: date, start_hour_utc: int, duration_hours: int) -> tuple[datetime, datetime]:
    start = datetime(day.year, day.month, day.day, start_hour_utc, tzinfo=timezone.utc)
    return start, start + timedelta(hours=duration_hours)


def estimate_for(
    announced_day: date | None,
    now: datetime,
    start_hour_utc: int = DEFAULT_START_HOUR_UTC,
    duration_hours: int = DEFAULT_DURATION_HOURS,
    extra: timedelta = timedelta(0),
    ended_early: bool = False,
) -> Estimate | None:
    """None se non c'è una manutenzione annunciata. extra: proroga aggiunta a mano;
    ended_early: segnalata a mano come già finita."""
    if announced_day is None:
        return None
    start, end = window_for(announced_day, start_hour_utc, duration_hours)
    end += extra
    if ended_early and now >= start:
        return Estimate(OVER, start, min(end, now))
    if now < start:
        return Estimate(UPCOMING, start, end)
    return Estimate(ACTIVE if now < end else OVER, start, end)


def adjustable(estimate: Estimate | None, now: datetime) -> bool:
    """Se ha senso offrire "+1 ora" / "È già finita": dall'inizio stimato fino a poco dopo la fine."""
    return estimate is not None and estimate.start <= now < estimate.end + GRACE_AFTER_END


def apply_estimate(statuses: dict[str, RegionStatus], estimate: Estimate | None) -> dict[str, RegionStatus]:
    """Copia di `statuses` in cui le regioni che l'API dà online sono segnate in manutenzione
    stimata, se la finestra stimata è in corso. Non tocca mai quello che dice l'API."""
    if estimate is None or estimate.phase != ACTIVE:
        return statuses
    result = dict(statuses)
    for region in ESTIMATED_REGIONS:
        status = result.get(region)
        if status is not None and not status.in_maintenance:
            result[region] = replace(status, in_maintenance=True, ends_at=estimate.end, estimated=True)
    return result
