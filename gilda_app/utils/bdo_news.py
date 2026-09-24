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
_TITLE_DATE_RE = re.compile(r"\b(" + "|".join(_MONTHS) + r")\s+(\d{1,2})\b", re.IGNORECASE)


@dataclass
class NewsItem:
    title: str
    url: str
    posted: date | None
    is_maintenance: bool
    maintenance_date: date | None


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
    if not match or posted is None:
        return None
    month, day = _MONTHS[match.group(1).lower()], int(match.group(2))
    try:
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
            )
        )
    return items


def upcoming_maintenance(items: list[NewsItem], today: date) -> NewsItem | None:
    """L'annuncio di manutenzione più vicino tra oggi e il futuro, se ce n'è uno."""
    candidates = [i for i in items if i.maintenance_date is not None and i.maintenance_date >= today]
    return min(candidates, key=lambda i: i.maintenance_date) if candidates else None


def fetch_news(api_key: str) -> list[NewsItem]:
    return parse_news(api_get("/api/news", api_key, {"board_type": NOTICES_BOARD_TYPE, "limit": NEWS_LIMIT}))
