"""Temi stagionali: nei periodi di festa cambiano la schermata di caricamento, il logo dell'intestazione,
una scritta di auguri e il colore d'accento; finito il periodo tutto torna come prima da solo.

Un tema è attivo se la data cade nel suo periodo e se i suoi file immagine ci sono (un tema senza
immagini resta spento: per aggiungerne uno basta mettere i file in resources/ e descriverlo in SEASONS).
Il comportamento si sceglie in Impostazioni: "auto" (default), "off", oppure il nome di un tema per
provarlo fuori stagione."""
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

RESOURCES = Path(__file__).resolve().parent / "resources"
SEASON_MODE_SETTING = "season_mode"
MODE_AUTO = "auto"
MODE_OFF = "off"
DEFAULT_ACCENT = "#009faa"  # colore d'accento normale (quello predefinito di qfluentwidgets)


@dataclass(frozen=True)
class Season:
    key: str  # anche parte dei nomi dei file: splash_<key>.png, wordmark_<key>.png
    start: tuple[int, int]  # (mese, giorno) di inizio, incluso
    end: tuple[int, int]  # (mese, giorno) di fine, incluso; può essere nell'anno dopo (Natale)
    accent: str | None  # colore d'accento dei pulsanti nel periodo (None = invariato)
    loading_color: str  # colore della scritta "Loading..." nella schermata stagionale
    # Giorni in cui compare la scritta di auguri (nel caricamento e in dashboard); None = tutto il periodo.
    # Fuori da questi giorni il tema resta (immagini, colore) ma senza gli auguri.
    greeting_start: tuple[int, int] | None = None
    greeting_end: tuple[int, int] | None = None

    @property
    def splash_path(self) -> Path:
        return RESOURCES / f"splash_{self.key}.png"

    @property
    def wordmark_path(self) -> Path:
        return RESOURCES / f"wordmark_{self.key}.png"

    @property
    def icon_path(self) -> Path:
        """Icona del programma nel periodo (finestra e barra delle applicazioni); se manca resta quella normale."""
        return RESOURCES / f"icon_{self.key}.png"

    def decor_path(self, name: str) -> Path:
        """Una decorazione del tema (vedi ui/season_decor.py): può non esistere, e allora si salta."""
        return RESOURCES / f"deco_{self.key}_{name}.png"

    @property
    def available(self) -> bool:
        return self.splash_path.exists() and self.wordmark_path.exists()

    def contains(self, day: date) -> bool:
        today = (day.month, day.day)
        if self.start <= self.end:
            return self.start <= today <= self.end
        return today >= self.start or today <= self.end  # a cavallo dell'anno nuovo

    def greets(self, day: date) -> bool:
        """Se oggi è un giorno di auguri (es. "Buon Halloween" solo il 31 ottobre e il 1 novembre)."""
        if self.greeting_start is None or self.greeting_end is None:
            return self.contains(day)
        today = (day.month, day.day)
        if self.greeting_start <= self.greeting_end:
            return self.greeting_start <= today <= self.greeting_end
        return today >= self.greeting_start or today <= self.greeting_end


# Halloween: arancione zucca, un po' più rosso di quello degli avvisi di manutenzione annunciata (#d9730d), che
# compare solo in dashboard come scheda larga con testo: non si confonde con i pulsanti.
SEASONS = [
    Season("halloween", start=(10, 21), end=(11, 2), accent="#e8650a", loading_color="#ffb36b",
           greeting_start=(10, 31), greeting_end=(11, 1)),
    # Blu zaffiro come il ghiaccio del logo: né rosso né verde, che negli avvisi e negli stati hanno già un significato.
    Season("natale", start=(12, 8), end=(1, 6), accent="#2a6fdb", loading_color="#d8ecff",
           greeting_start=(12, 24), greeting_end=(1, 1)),
]


def active_season(today: date, mode: str = MODE_AUTO) -> Season | None:
    """Il tema da usare oggi, o None per l'aspetto normale. mode: "auto", "off" o la chiave di un tema."""
    if mode == MODE_OFF:
        return None
    if mode != MODE_AUTO:
        forced = next((s for s in SEASONS if s.key == mode and s.available), None)
        return forced
    return next((s for s in SEASONS if s.available and s.contains(today)), None)


def greeting_active(season: Season, today: date, mode: str = MODE_AUTO) -> bool:
    """Se mostrare gli auguri: nei giorni di festa, e sempre nella prova di un tema scelta in Impostazioni
    (altrimenti fuori stagione non si vedrebbero mai)."""
    return mode != MODE_AUTO or season.greets(today)


def selectable_modes() -> list[str]:
    """Le scelte per Impostazioni: automatico, spento e un tema per ogni stagione con le immagini pronte."""
    return [MODE_AUTO, MODE_OFF] + [s.key for s in SEASONS if s.available]


def read_setting(db_file: Path, key: str, default: str) -> str:
    """Legge un'impostazione dal database senza aprirlo davvero (sola lettura): serve alla schermata di
    avvio, che compare prima che il programma apra il database. Qualunque problema -> default."""
    if not db_file.exists():
        return default
    try:
        conn = sqlite3.connect(f"file:{db_file.as_posix()}?mode=ro", uri=True)
        try:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return default
    return row[0] if row and row[0] else default
