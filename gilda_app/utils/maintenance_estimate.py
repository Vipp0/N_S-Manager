"""Stima dell'orario della manutenzione, per quando l'API dice "online" a server spenti.

bdoalerts.net segnala la manutenzione solo quando se ne accorge (spesso mai), mentre gli
avvisi ufficiali danno la data ma non l'ora. Gli orari reali sono però quasi sempre gli stessi:
nel giorno di una manutenzione annunciata, dentro quella finestra, se l'API dice online lo
stato mostrato è "in manutenzione (stimata)". Se l'API dice invece manutenzione, vale l'API.

L'orario è ancorato all'ora della costa ovest degli Stati Uniti (Pacific Time): gli avvisi
ufficiali la elencano per prima, "01:00 - 05:00 PT", e la stessa manutenzione è 09:00-13:00 UTC
d'inverno e 08:00-12:00 UTC d'estate (verificato su avvisi di gennaio e di ottobre). In Italia
si legge quasi sempre 10:00-14:00, ma per qualche giorno l'anno (la settimana tra il cambio
d'ora europeo e quello americano in autunno, circa tre settimane in primavera) è un'ora prima:
è la "discrepanza" che si nota a ogni cambio d'ora, e qui viene da sé."""
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone

from gilda_app.utils.bdo_notice import PublishedSchedule
from gilda_app.utils.server_status import RegionStatus

DEFAULT_START_HOUR_PT = 1
DEFAULT_DURATION_HOURS = 4
# Una manutenzione "temporanea" (fuori dal calendario del giovedì) di solito dura 2 ore.
DEFAULT_TEMPORARY_HOURS = 2
MIN_DURATION_HOURS = 1
MAX_DURATION_HOURS = 12
# Gli avvisi letti (NA/EU PC) valgono per queste regioni; console, Corea, ecc. hanno altri orari.
ESTIMATED_REGIONS = ("eu", "na")
# Dopo la fine prevista si può ancora segnalare "è durata di più" per un po'.
GRACE_AFTER_END = timedelta(hours=3)
# Per quanto tempo, a manutenzione finita, la dashboard avvisa che i server sono tornati online.
BACK_ONLINE_BANNER = timedelta(minutes=30)

UPCOMING = "upcoming"
ACTIVE = "active"
OVER = "over"


@dataclass(frozen=True)
class Estimate:
    phase: str  # UPCOMING | ACTIVE | OVER
    start: datetime  # UTC
    end: datetime  # UTC, già comprensivo di eventuali proroghe
    official: bool = False  # l'orario viene dall'avviso ufficiale invece che dalla stima di riserva
    confirmed: bool = False  # la fine è stata segnalata a mano ("È già finita"), non dedotta dall'orario


def _nth_sunday(year: int, month: int, n: int) -> date:
    first = date(year, month, 1)
    first_sunday = first + timedelta(days=(6 - first.weekday()) % 7)
    return first_sunday + timedelta(weeks=n - 1)


def pacific_utc_offset(local: datetime) -> timedelta:
    """Differenza dall'UTC dell'ora della costa ovest USA in un dato momento (ora locale
    "da muro", senza fuso): -7h con l'ora legale (dalla seconda domenica di marzo alla prima
    di novembre, alle 02:00), -8h senza. Regola scritta qui per non dipendere dal database dei
    fusi orari, che su Windows non è incluso. Le ore ambigue del cambio non servono: la
    manutenzione cade di notte tra giovedì e venerdì, mai la domenica."""
    dst_start = datetime.combine(_nth_sunday(local.year, 3, 2), datetime.min.time()) + timedelta(hours=2)
    dst_end = datetime.combine(_nth_sunday(local.year, 11, 1), datetime.min.time()) + timedelta(hours=2)
    return timedelta(hours=-7) if dst_start <= local < dst_end else timedelta(hours=-8)


def parse_config(start_hour, duration_hours) -> tuple[int, int]:
    """(ora di inizio all'ora di Los Angeles, durata in ore) da valori salvati, con i valori di
    default se mancano o sono illeggibili."""
    try:
        start = int(start_hour)
    except (TypeError, ValueError):
        start = DEFAULT_START_HOUR_PT
    try:
        hours = int(duration_hours)
    except (TypeError, ValueError):
        hours = DEFAULT_DURATION_HOURS
    return max(0, min(23, start)), max(MIN_DURATION_HOURS, min(MAX_DURATION_HOURS, hours))


def parse_temporary_hours(value) -> int:
    """Durata (ore) di una manutenzione temporanea da un valore salvato, con default se manca."""
    try:
        hours = int(value)
    except (TypeError, ValueError):
        hours = DEFAULT_TEMPORARY_HOURS
    return max(MIN_DURATION_HOURS, min(MAX_DURATION_HOURS, hours))


def window_for(day: date, start_hour_pt: int, duration_hours: int) -> tuple[datetime, datetime]:
    """Inizio e fine (UTC) della manutenzione del giorno `day`, che inizia alle `start_hour_pt`
    ora di Los Angeles."""
    local = datetime(day.year, day.month, day.day, start_hour_pt)
    start = (local - pacific_utc_offset(local)).replace(tzinfo=timezone.utc)
    return start, start + timedelta(hours=duration_hours)


def estimate_for(
    announced_day: date | None,
    now: datetime,
    start_hour_pt: int = DEFAULT_START_HOUR_PT,
    duration_hours: int = DEFAULT_DURATION_HOURS,
    extra: timedelta = timedelta(0),
    ended_at: datetime | None = None,
    published: PublishedSchedule | None = None,
) -> Estimate | None:
    """None se non c'è una manutenzione annunciata. extra: proroga aggiunta a mano;
    ended_at: il momento in cui è stata segnalata a mano come già finita. published: orario letto dall'avviso
    ufficiale, che se c'è (ed è dello stesso giorno) vale più della stima di riserva."""
    if announced_day is None:
        return None
    official = published is not None and published.day == announced_day
    if official:
        start, end = published.start, published.end
    else:
        start, end = window_for(announced_day, start_hour_pt, duration_hours)
    end += extra
    if ended_at is not None and ended_at >= start:
        return Estimate(OVER, start, min(end, ended_at), official, confirmed=True)
    if now < start:
        return Estimate(UPCOMING, start, end, official)
    return Estimate(ACTIVE if now < end else OVER, start, end, official)


def recently_finished(estimate: Estimate | None, now: datetime) -> bool:
    """Se la manutenzione è finita da poco (meno di BACK_ONLINE_BANNER): è il momento di dire in
    dashboard che i server sono tornati online."""
    return estimate is not None and estimate.phase == OVER and timedelta(0) <= now - estimate.end < BACK_ONLINE_BANNER


def pending_notices(
    candidates,
    now: datetime,
    start_hour_pt: int,
    duration_hours: int,
    temporary_hours: int,
    published_for=None,
    adjust_for=None,
) -> list:
    """Tra gli annunci (già in ordine di data) quelli che interessano ancora, nello stesso ordine:
    quelli la cui manutenzione è finita da più di BACK_ONLINE_BANNER si saltano. Senza questo, il
    giovedì sera restava "l'annuncio" quello della manutenzione ordinaria già finita, e l'avviso del
    giorno dopo (una temporanea) non compariva fino a mezzanotte.
    published_for(item) -> orario letto dall'avviso o None; adjust_for(giorno) -> (proroga, fine segnalata)."""
    result = []
    for item in candidates:
        extra, ended_at = adjust_for(item.maintenance_date) if adjust_for else (timedelta(0), None)
        published = published_for(item) if published_for else None
        hours = temporary_hours if item.is_temporary else duration_hours
        estimate = estimate_for(item.maintenance_date, now, start_hour_pt, hours, extra, ended_at, published)
        if estimate is not None and estimate.phase == OVER and now - estimate.end >= BACK_ONLINE_BANNER:
            continue
        result.append(item)
    return result


def pick_current(candidates, *args, **kwargs):
    """Il primo annuncio che interessa ancora (vedi pending_notices), o None."""
    pending = pending_notices(candidates, *args, **kwargs)
    return pending[0] if pending else None


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
            result[region] = replace(status, in_maintenance=True, ends_at=estimate.end, estimated=True, official=estimate.official)
    return result
