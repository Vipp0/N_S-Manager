import os
import re
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from gilda_app.utils.paths import backups_dir

EXTRA_DIR_SETTING = "extra_backup_dir"
AUTO_REASON = "auto"
AUTO_BACKUPS_TO_KEEP = 30
# Con il programma aperto per giorni (e il PC sempre acceso) la copia dell'avvio non basta: ogni
# notte, a quest'ora locale, se non c'è ancora una copia automatica più recente se ne fa una.
NIGHTLY_BACKUP_HOUR = 2

_NAME_RE = re.compile(r"^gilda_(\d{8})_(\d{6})_(.+)\.db$")


@dataclass
class BackupResult:
    path: Path | None
    extra_error: str | None = None


@dataclass
class BackupInfo:
    path: Path
    created: datetime
    reason: str
    size: int


def _copy_to_extra(src: Path, extra_dir: Path) -> str | None:
    """Copia il backup nella cartella extra. Ritorna il messaggio d'errore, o None."""
    try:
        extra_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, extra_dir / src.name)
    except OSError as exc:
        return str(exc)
    return None


def backup_database(
    db_path: Path, reason: str, extra_dir: Path | None = None, conn: sqlite3.Connection | None = None
) -> BackupResult:
    """conn: connessione aperta al database. Con la connessione si usa la copia "online" di
    SQLite, che dà un'istantanea coerente anche se un altro thread sta scrivendo; senza,
    si copia il file (come all'avvio, quando il database non è ancora aperto)."""
    if not db_path.exists():
        return BackupResult(None)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backups_dir() / f"gilda_{timestamp}_{reason}.db"
    if conn is not None:
        target = sqlite3.connect(str(dest))
        try:
            conn.backup(target)
        finally:
            target.close()
    else:
        shutil.copy2(db_path, dest)
    error = _copy_to_extra(dest, extra_dir) if extra_dir is not None else None
    return BackupResult(dest, error)


def _parse_backup(path: Path) -> BackupInfo | None:
    match = _NAME_RE.match(path.name)
    if match is None:
        return None
    try:
        created = datetime.strptime(match.group(1) + match.group(2), "%Y%m%d%H%M%S")
        size = path.stat().st_size
    except (ValueError, OSError):
        return None
    return BackupInfo(path, created, match.group(3), size)


def list_backups(*directories: Path) -> list[BackupInfo]:
    """Backup presenti nelle cartelle indicate, dal più recente. Se lo stesso file è in
    più cartelle (copia extra) compare una volta sola, con la prima cartella data."""
    seen: dict[str, BackupInfo] = {}
    for directory in directories:
        if directory is None or not directory.is_dir():
            continue
        for path in directory.glob("gilda_*.db"):
            info = _parse_backup(path)
            if info is not None and path.name not in seen:
                seen[path.name] = info
    return sorted(seen.values(), key=lambda b: b.created, reverse=True)


def prune_auto_backups(directory: Path, keep: int = AUTO_BACKUPS_TO_KEEP) -> None:
    """Tiene solo gli ultimi `keep` backup automatici; gli altri tipi (spostamenti,
    import, manuali...) non si toccano."""
    autos = [b for b in list_backups(directory) if b.reason == AUTO_REASON]
    for old in autos[keep:]:
        try:
            old.path.unlink()
        except OSError:
            pass


def read_extra_backup_dir(db_path: Path) -> Path | None:
    """Legge la cartella extra dal database prima che l'app lo apra (serve al backup
    all'avvio, che deve avvenire prima delle migrazioni)."""
    if not db_path.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        try:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (EXTRA_DIR_SETTING,)).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    return Path(row[0]) if row and row[0] else None


def daily_backup_if_needed(db_path: Path) -> BackupResult | None:
    """Un backup automatico al giorno, fatto all'avvio prima di aprire il database (quindi
    prima di un'eventuale migrazione dello schema). Ritorna None se oggi c'è già."""
    if not db_path.exists():
        return None
    extra_dir = read_extra_backup_dir(db_path)
    today = datetime.now().date()
    if any(b.reason == AUTO_REASON and b.created.date() == today for b in list_backups(backups_dir())):
        return None
    result = backup_database(db_path, AUTO_REASON, extra_dir)
    prune_auto_backups(backups_dir())
    if extra_dir is not None:
        prune_auto_backups(extra_dir)
    return result


def latest_auto_backup_time(*directories: Path) -> datetime | None:
    """Quando è stata fatta l'ultima copia automatica (nelle cartelle indicate)."""
    autos = [b.created for b in list_backups(*directories) if b.reason == AUTO_REASON]
    return max(autos) if autos else None


def nightly_backup_due(now: datetime, latest_auto: datetime | None, hour: int = NIGHTLY_BACKUP_HOUR) -> bool:
    """Se è ora di una copia notturna: c'è stato un passaggio dell'orario `hour` dopo l'ultima
    copia automatica. Vale anche a ritardo (PC in sospensione alle 2, programma riaperto dopo):
    la copia si fa appena possibile invece di saltare la notte."""
    boundary = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if now < boundary:
        boundary -= timedelta(days=1)
    return latest_auto is None or latest_auto < boundary


def is_valid_backup(path: Path) -> bool:
    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        try:
            conn.execute("SELECT COUNT(*) FROM members").fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return False
    return True


def restore_backup(backup_path: Path, db_path: Path) -> None:
    """Sostituisce il database con il backup. La connessione all'app va chiusa prima.
    Copia su un file temporaneo e poi lo sostituisce di colpo, così un errore a metà
    non lascia mai un database a metà."""
    tmp = db_path.with_name(db_path.name + ".restoring")
    try:
        shutil.copyfile(backup_path, tmp)
        os.replace(tmp, db_path)
    finally:
        if tmp.exists():
            tmp.unlink()
