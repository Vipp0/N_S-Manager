"""Posti della gilda: il numero massimo di membri (in Black Desert una gilda arriva a 100). Serve alla barra dei
posti della dashboard; superarlo non blocca niente, la barra diventa solo ambra e dice di quanto."""
import sqlite3

from gilda_app.db.database import get_setting

GUILD_CAPACITY_SETTING = "guild_capacity"
DEFAULT_GUILD_CAPACITY = 100
MIN_GUILD_CAPACITY = 1
MAX_GUILD_CAPACITY = 500


def guild_capacity(conn: sqlite3.Connection) -> int:
    """Il valore salvato in Impostazioni; se manca o non è un numero sensato, il predefinito."""
    try:
        value = int(get_setting(conn, GUILD_CAPACITY_SETTING, str(DEFAULT_GUILD_CAPACITY)))
    except (TypeError, ValueError):
        return DEFAULT_GUILD_CAPACITY
    return value if MIN_GUILD_CAPACITY <= value <= MAX_GUILD_CAPACITY else DEFAULT_GUILD_CAPACITY
