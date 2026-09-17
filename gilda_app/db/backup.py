import shutil
from datetime import datetime
from pathlib import Path

from gilda_app.utils.paths import backups_dir


def backup_database(db_path: Path, reason: str) -> Path | None:
    if not db_path.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backups_dir() / f"gilda_{timestamp}_{reason}.db"
    shutil.copy2(db_path, dest)
    return dest
