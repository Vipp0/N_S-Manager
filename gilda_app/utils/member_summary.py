"""I dati del pannello dei dettagli di un membro (schermate Membri attuali, Ex membri, Bannati): da quando è in
gilda, quando è uscito o è stato bannato, il motivo, un'etichetta "Nuovo" o "Rientrato" e gli ultimi passaggi.
Si ricava dal membro e dalla sua cronologia dei movimenti (status_history); niente interfaccia qui, per poterlo
provare da solo.

Le date che il programma non conosce non si inventano: se manca la data di ingresso lo si dice (missing_join_date)
e la cronologia mostra "data sconosciuta"."""
from dataclasses import dataclass, field
from datetime import date

from gilda_app.i18n import tr
from gilda_app.models.member import STATUS_ATTIVO, STATUS_BANNATO, STATUS_EX_MEMBRO, Member
from gilda_app.utils.date_format import iso_to_display

RECENT_DAYS = 30  # per quanto tempo un membro è "Nuovo" o "Rientrato"

TONE_GOOD, TONE_BAD, TONE_NEUTRAL = "good", "bad", "neutral"  # come i toni di chips.py (qui senza dipendere dall'interfaccia)
TAG_NEW, TAG_REJOINED = "new", "rejoined"


@dataclass
class HistoryItem:
    key: str  # "joined", "rejoined", "left", "banned", "added", "moved": è il nome dell'etichetta (chip.<key>)
    day: str  # data già nel formato da mostrare
    tone: str
    note: str = ""


@dataclass
class MemberSummary:
    tag: str | None = None  # TAG_NEW, TAG_REJOINED o None
    in_guild: str = ""  # la riga principale: "Dal ... · ...", "Rientrato il ...", "Uscito il ...", "Bannato il ..."
    first_join: str = ""  # "Primo ingresso il ..." per chi è rientrato
    missing_join_date: bool = False  # membro attuale senza data di ingresso
    ban_reason: str = ""  # la nota registrata quando è stato bannato
    history: list[HistoryItem] = field(default_factory=list)  # dal più recente


def _day(stamp: str | None) -> date | None:
    try:
        return date.fromisoformat(stamp[:10]) if stamp else None
    except ValueError:
        return None


def duration_text(start: date, end: date) -> str:
    """"3 giorni", "8 mesi", "2 anni e 11 mesi": la durata tra due date, come la si dice a voce."""
    months_total = (end.year - start.year) * 12 + end.month - start.month - (1 if end.day < start.day else 0)
    if months_total < 1:
        days = max(0, (end - start).days)
        return tr("duration.day_one") if days == 1 else tr("duration.day_many", n=days)
    years, months = divmod(months_total, 12)
    parts = []
    if years:
        parts.append(tr("duration.year_one") if years == 1 else tr("duration.year_many", n=years))
    if months:
        parts.append(tr("duration.month_one") if months == 1 else tr("duration.month_many", n=months))
    return f" {tr('duration.and')} ".join(parts)


def _history_item(row) -> HistoryItem:
    previous, new = row["previous_status"], row["new_status"]
    stamp = row["changed_at"]
    day = iso_to_display(stamp) if stamp else tr("history.unknown_date")
    if previous is None:
        key, tone = ("joined", TONE_GOOD) if new == STATUS_ATTIVO else ("added", TONE_NEUTRAL)
    elif new == STATUS_ATTIVO:
        key, tone = "rejoined", TONE_GOOD
    elif previous == STATUS_ATTIVO:
        key, tone = ("banned", TONE_BAD) if new == STATUS_BANNATO else ("left", TONE_BAD)
    else:
        key, tone = "moved", TONE_NEUTRAL  # tra ex membro e bannato
    return HistoryItem(key, day, tone, row["note"] or "")


def summarize(member: Member, history_rows: list, today: date) -> MemberSummary:
    """history_rows: le righe di status_history del membro in ordine di registrazione (previous_status, new_status,
    changed_at, note)."""
    summary = MemberSummary(history=[_history_item(row) for row in reversed(history_rows)])
    first_join = _day(member.data_inserimento)

    entered = first_join  # da quando è in gilda nel periodo che si sta guardando
    rejoin_day = left_day = banned_day = None
    for row in history_rows:
        day = _day(row["changed_at"])
        if row["previous_status"] is None:
            continue
        if row["new_status"] == STATUS_ATTIVO:
            entered, rejoin_day = day or entered, day
            left_day = banned_day = None
        elif row["previous_status"] == STATUS_ATTIVO:
            left_day = day
            if row["new_status"] == STATUS_BANNATO:
                banned_day, summary.ban_reason = day, row["note"] or ""
        elif row["new_status"] == STATUS_BANNATO:  # da ex membro a bannato
            banned_day, summary.ban_reason = day, row["note"] or ""

    if member.status == STATUS_ATTIVO:
        if rejoin_day is not None:
            summary.in_guild = tr("panel.rejoined_on", date=iso_to_display(rejoin_day.isoformat()), duration=_since(rejoin_day, today))
            if first_join is not None:
                summary.first_join = tr("panel.first_join", date=iso_to_display(first_join.isoformat()))
            if (today - rejoin_day).days <= RECENT_DAYS:
                summary.tag = TAG_REJOINED
        elif first_join is not None:
            summary.in_guild = tr("panel.since", date=iso_to_display(first_join.isoformat()), duration=_since(first_join, today))
            if (today - first_join).days <= RECENT_DAYS:
                summary.tag = TAG_NEW
        else:
            summary.missing_join_date = True
    elif member.status == STATUS_EX_MEMBRO:
        if left_day is None:
            summary.in_guild = tr("panel.left_unknown")
        else:
            summary.in_guild = tr("panel.left_on", date=iso_to_display(left_day.isoformat()))
            if entered is not None and left_day >= entered:
                summary.in_guild += tr("panel.after", duration=duration_text(entered, left_day))
    else:
        summary.in_guild = (
            tr("panel.banned_on", date=iso_to_display(banned_day.isoformat())) if banned_day else tr("panel.banned_unknown")
        )
    return summary


def _since(start: date, today: date) -> str:
    """"da oggi" o "da 8 mesi"."""
    return tr("panel.since_today") if start >= today else tr("panel.for", duration=duration_text(start, today))
