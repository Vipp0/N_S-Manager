"""Percorsi dell'applicazione: in dev usa la root del progetto, da .exe usa la cartella dell'eseguibile."""
import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def db_path() -> Path:
    return app_dir() / "gilda.db"


def backups_dir() -> Path:
    d = app_dir() / "backups"
    d.mkdir(exist_ok=True)
    return d
