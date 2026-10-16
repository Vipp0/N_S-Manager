"""Avvisi ufficiali di Black Desert (NA/EU) letti da bdoalerts.net, in particolare gli
annunci di manutenzione. Nessuna stima: la data di una manutenzione si ricava solo dal
titolo dell'avviso ufficiale (es. "September 30 (Wed) Maintenance"); l'orario non c'è
nei dati e resta nella pagina dell'avviso, raggiungibile dal link."""
import re
from dataclasses import dataclass
from datetime import date, timedelta

from gilda_app.utils.bdoalerts_api import ERROR_BAD_RESPONSE, ApiError, api_get

NOTICES_BOARD_TYPE = 1
NEWS_LIMIT = 10

_MONTHS = {
    name: index
    for index, name in enumerate(
        ["january", "february", "march", "april", "may", "june", "july",
         "august", "september", "october", "november", "december"],
        start=1,
    )
}
_POSTED_RE = re.compile(r"([A-Za-z]{3})[a-z]* (\d{1,2}), (\d{4})")
# "October 8 (Thu) Maintenance" ma anche "Oct 16, 2026 (Fri) - Temporary Maintenance": mese per
# esteso o abbreviato (le forme lunghe prima, altrimenti "Sep" si mangerebbe "September"), anno facoltativo.
_MONTH_WORDS = sorted(list(_MONTHS) + ["jan", "feb", "mar", "apr", "jun", "jul", "aug", "sept", "sep", "oct", "nov", "dec"],
                      key=len, reverse=True)
_TITLE_DATE_RE = re.compile(
    r"\b(" + "|".join(_MONTH_WORDS) + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b(?:,?\s*(\d{4}))?", re.IGNORECASE
)
# Avvisi di manutenzione fuori dal solito calendario del giovedì: durano meno (di solito 2 ore).
_TEMPORARY_WORDS = ("temporary", "emergency")
# Manutenzioni di servizi che non fermano il gioco ("Central Market Maintenance": il gioco resta
# acceso, e di solito dura una ventina di minuti): non sono la manutenzione dei server.
_NOT_SERVER_WORDS = ("central market", "website", "web site", "payment", "forum", "pearl shop")


@dataclass
class NewsItem:
    title: str
    url: str
    posted: date | None
    is_maintenance: bool
    maintenance_date: date | None
    is_temporary: bool = False  # "Temporary Maintenance": fuori calendario, più breve
    affects_servers: bool = True  # False per manutenzioni del solo mercato, sito, pagamenti...


def _parse_posted(text) -> date | None:
    match = _POSTED_RE.search(text) if isinstance(text, str) else None
    if not match:
        return None
    prefix = match.group(1).lower()
    month = next((index for name, index in _MONTHS.items() if name.startswith(prefix)), None)
    if month is None:
        return None
    try:
        return date(int(match.group(3)), month, int(match.group(2)))
    except ValueError:
        return None


def _parse_maintenance_date(title: str, posted: date | None) -> date | None:
    match = _TITLE_DATE_RE.search(title)
    if not match or (posted is None and not match.group(3)):
        return None
    word = match.group(1).lower()
    month = _MONTHS[word] if word in _MONTHS else next(i for name, i in _MONTHS.items() if name.startswith(word[:3]))
    day = int(match.group(2))
    try:
        if match.group(3):  # l'anno scritto nel titolo vale più di quello dedotto dalla data di pubblicazione
            return date(int(match.group(3)), month, day)
        result = date(posted.year, month, day)
    except ValueError:
        return None
    # Avviso pubblicato a fine dicembre per una manutenzione di gennaio.
    if result < posted - timedelta(days=180):
        result = result.replace(year=result.year + 1)
    return result


def parse_news(payload: dict) -> list[NewsItem]:
    updates = payload.get("updates")
    if not isinstance(updates, list):
        raise ApiError(ERROR_BAD_RESPONSE)
    items = []
    for raw in updates:
        if not isinstance(raw, dict) or not isinstance(raw.get("title"), str):
            continue
        title = raw["title"].strip()
        posted = _parse_posted(raw.get("date_posted"))
        is_maintenance = "maintenance" in title.lower()
        url = raw.get("url") if isinstance(raw.get("url"), str) else ""
        items.append(
            NewsItem(
                title=title,
                url=url if url.startswith("https://") else "",
                posted=posted,
                is_maintenance=is_maintenance,
                maintenance_date=_parse_maintenance_date(title, posted) if is_maintenance else None,
                is_temporary=is_maintenance and any(word in title.lower() for word in _TEMPORARY_WORDS),
                affects_servers=not any(word in title.lower() for word in _NOT_SERVER_WORDS),
            )
        )
    return items


def upcoming_maintenance(items: list[NewsItem], today: date) -> NewsItem | None:
    """L'annuncio di manutenzione più vicino tra oggi e il futuro, se ce n'è uno."""
    candidates = [
        i for i in items if i.maintenance_date is not None and i.maintenance_date >= today and i.affects_servers
    ]
    return min(candidates, key=lambda i: i.maintenance_date) if candidates else None


def fetch_news(api_key: str) -> list[NewsItem]:
    return parse_news(api_get("/api/news", api_key, {"board_type": NOTICES_BOARD_TYPE, "limit": NEWS_LIMIT}))
