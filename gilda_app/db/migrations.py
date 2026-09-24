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


def _upgrade_3(conn: sqlite3.Connection) -> None:
    # Rilevante solo per gli ex membri: sono ancora presenti nel canale Discord della
    # gilda pur non essendo più membri attivi. Colonna su members (non una tabella a
    # parte) perché è un singolo valore per persona, non uno storico.
    conn.executescript(
        """
        ALTER TABLE members ADD COLUMN still_on_discord INTEGER NOT NULL DEFAULT 0;
        """
    )


def _upgrade_4(conn: sqlite3.Connection) -> None:
    # Un evento ricorrente è una riga sola (una "serie"): le occorrenze si calcolano al
    # volo per il mese mostrato (vedi db/calendar_events.py), non si salvano una per una.
    conn.executescript(
        """
        CREATE TABLE calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_date TEXT NOT NULL,
            title TEXT NOT NULL,
            note TEXT,
            color TEXT NOT NULL DEFAULT '#0078d4',
            recurrence_unit TEXT NOT NULL DEFAULT 'none'
                CHECK (recurrence_unit IN ('none', 'daily', 'weekly', 'monthly')),
            recurrence_interval INTEGER NOT NULL DEFAULT 1,
            recurrence_end_date TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX idx_calendar_events_start_date ON calendar_events(start_date);
        """
    )


def _upgrade_5(conn: sqlite3.Connection) -> None:
    # Festività della Corea del Sud (vedi db/holidays.py): tabella "usa e getta",
    # ricostruita per intero ad ogni aggiornamento riuscito dalla fonte online, mai
    # modificata a mano dall'utente.
    conn.executescript(
        """
        CREATE TABLE holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(date, name)
        );
        CREATE INDEX idx_holidays_date ON holidays(date);
        """
    )


def _upgrade_6(conn: sqlite3.Connection) -> None:
    # Storico dei cambi di nome di un membro. "field" dice quale nome è cambiato (oggi solo
    # family_name, ma la struttura regge anche main_name/discord_name senza altre modifiche).
    conn.executescript(
        """
        CREATE TABLE name_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
            field TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT NOT NULL,
            changed_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX idx_name_history_member ON name_history(member_id);
        """
    )


MIGRATIONS = [_upgrade_1, _upgrade_2, _upgrade_3, _upgrade_4, _upgrade_5, _upgrade_6]


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
