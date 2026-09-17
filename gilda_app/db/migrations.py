"""Schema versionato: ogni funzione upgrade_N porta dalla versione N-1 alla N."""
import sqlite3


def _upgrade_1(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_name TEXT NOT NULL,
            main_name TEXT,
            discord_name TEXT,
            status TEXT NOT NULL CHECK (status IN ('attivo', 'ex_membro', 'bannato')),
            data_inserimento TEXT,
            note TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE member_nations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
            nation TEXT NOT NULL,
            ord INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
            previous_status TEXT,
            new_status TEXT NOT NULL,
            changed_at TEXT NOT NULL DEFAULT (datetime('now')),
            note TEXT
        );

        CREATE INDEX idx_members_name ON members(family_name, main_name);
        CREATE INDEX idx_members_status ON members(status);
        CREATE INDEX idx_member_nations_member ON member_nations(member_id);
        CREATE INDEX idx_status_history_member ON status_history(member_id);
        """
    )


def _upgrade_2(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )


MIGRATIONS = [_upgrade_1, _upgrade_2]


def migrate(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
    row = conn.execute("SELECT version FROM schema_version").fetchone()
    current = row[0] if row else 0

    for version, upgrade in enumerate(MIGRATIONS, start=1):
        if version > current:
            upgrade(conn)
            current = version

    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (current,))
    else:
        conn.execute("UPDATE schema_version SET version = ?", (current,))
    conn.commit()
