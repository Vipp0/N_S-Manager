"""Orario di una manutenzione letto dall'avviso ufficiale (la pagina linkata dalle news).

L'API di bdoalerts.net non dà l'orario, ma la pagina dell'avviso ha una sezione "Maintenance
Schedule" con durata e orari in più fusi (PT/PDT, ET/EDT, UTC, CEST/CET), sempre nello stesso
ordine. Si legge solo l'orario UTC del primo blocco (il gioco: i blocchi seguenti sono il sito
web, che si ferma di meno). Qualunque cosa vada storto (sito cambiato, rete assente, pagina
inattesa) restituisce None e il programma ripiega sulla stima di maintenance_estimate.py:
nessun errore da mostrare e niente che si rompe."""
import re
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse

FETCH_TIMEOUT_SECONDS = 10
# Si scarica solo dal sito ufficiale: l'indirizzo arriva da un servizio esterno (l'API delle news).
ALLOWED_HOST_SUFFIX = ".playblackdesert.com"

_RANGE_RE = re.compile(r"^(\d{1,2}):(\d{2})\s*[-–~]\s*(\d{1,2}):(\d{2})$")
_ZONE_RE = re.compile(r"^[A-Z]{2,4}$")


@dataclass(frozen=True)
class PublishedSchedule:
    """Inizio e fine (UTC) dell'avviso ufficiale per il giorno `day`."""

    day: date
    start: datetime
    end: datetime
    reason: str = ""  # "Maintenance Reason" dell'avviso (nelle temporanee), nel testo originale, una frase per riga


def _text_lines(html: str) -> list[str]:
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", "\n", html)
    text = re.sub(r"&nbsp;|&#160;", " ", html)
    return [line.strip() for line in re.sub(r"[ \t\r\f\v]+", " ", text).split("\n") if line.strip()]


MAX_REASON_CHARS = 500


def parse_reason(lines: list[str]) -> str:
    """Il motivo scritto nell'avviso ("■ Maintenance Reason:" seguito da una o più frasi), nel testo
    originale in inglese. Vuoto se la sezione non c'è (le manutenzioni ordinarie non la hanno)."""
    try:
        index = next(i for i, line in enumerate(lines) if "maintenance reason" in line.lower())
    except StopIteration:
        return ""
    parts: list[str] = []
    for line in lines[index + 1 : index + 12]:
        lowered = line.lower()
        if line.startswith("■") or "maintenance impact" in lowered or "we appreciate" in lowered or "thank you" in lowered:
            break
        parts.append(line.lstrip("-•· ").strip())
    text = "\n".join(part for part in parts if part)  # una riga per frase/voce, come nell'avviso
    return text[: MAX_REASON_CHARS - 1] + "…" if len(text) > MAX_REASON_CHARS else text


def parse_schedule(html: str, day: date) -> PublishedSchedule | None:
    """Orario UTC del primo "Maintenance Schedule" della pagina, riferito al giorno `day`
    (quello del titolo dell'avviso). None se la sezione manca o non ha la forma attesa."""
    lines = _text_lines(html)
    try:
        index = next(i for i, line in enumerate(lines) if "maintenance schedule" in line.lower())
    except StopIteration:
        return None
    zones: list[str] = []
    ranges: list[tuple[int, int, int, int]] = []
    for line in lines[index + 1 : index + 25]:
        match = _RANGE_RE.match(line)
        if match:
            ranges.append(tuple(int(g) for g in match.groups()))
        elif ranges:
            break  # finite le righe degli orari
        elif _ZONE_RE.match(line):
            zones.append(line)
        # la riga della durata ("4 hours") e le altre si saltano
    if not zones or len(zones) != len(ranges) or "UTC" not in zones:
        return None
    sh, sm, eh, em = ranges[zones.index("UTC")]
    if not (0 <= sh < 24 and 0 <= eh < 24 and 0 <= sm < 60 and 0 <= em < 60):
        return None
    start = datetime(day.year, day.month, day.day, sh, sm, tzinfo=timezone.utc)
    end = datetime(day.year, day.month, day.day, eh, em, tzinfo=timezone.utc)
    if end <= start:  # a cavallo della mezzanotte
        end += timedelta(days=1)
    return PublishedSchedule(day, start, end, parse_reason(lines))


def is_official_url(url: str) -> bool:
    parts = urlparse(url or "")
    host = parts.hostname or ""
    return parts.scheme == "https" and (host.endswith(ALLOWED_HOST_SUFFIX) or host == ALLOWED_HOST_SUFFIX[1:])


def fetch_schedule(url: str, day: date) -> PublishedSchedule | None:
    """Scarica la pagina dell'avviso e ne legge l'orario. Non solleva mai."""
    if not is_official_url(url):
        return None
    request = urllib.request.Request(url, headers={"User-Agent": "Night-Shade-Manager", "Accept-Language": "en-US"})
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            html = response.read(2_000_000).decode("utf-8", errors="replace")
        return parse_schedule(html, day)
    except Exception:
        return None
