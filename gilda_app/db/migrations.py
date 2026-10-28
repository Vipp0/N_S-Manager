"""Schema versionato: ogni funzione upgrade_N porta dalla versione N-1 alla N."""
import json
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


def _upgrade_7(conn: sqlite3.Connection) -> None:
    # Compleanno del membro: "MM-DD" oppure "YYYY-MM-DD" (l'anno è facoltativo).
    conn.executescript("ALTER TABLE members ADD COLUMN birthday TEXT;")


def _upgrade_8(conn: sqlite3.Connection) -> None:
    # Un passaggio dello storico può avere "data sconosciuta" (NULL): quando si ricostruisce
    # uno storico a posteriori non sempre si conosce la data di ogni passaggio. SQLite non
    # permette di togliere NOT NULL da una colonna, quindi si ricrea la tabella.
    conn.executescript(
        """
        CREATE TABLE status_history_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
            previous_status TEXT,
            new_status TEXT NOT NULL,
            changed_at TEXT DEFAULT (datetime('now')),
            note TEXT
        );
        INSERT INTO status_history_new (id, member_id, previous_status, new_status, changed_at, note)
            SELECT id, member_id, previous_status, new_status, changed_at, note FROM status_history;
        DROP TABLE status_history;
        ALTER TABLE status_history_new RENAME TO status_history;
        CREATE INDEX idx_status_history_member ON status_history(member_id);
        """
    )


# Fin dove si recuperano dallo storico esistente gli eventi già accaduti: il programma ha meno di 90 giorni di
# vita, quindi sono tutte le operazioni fatte con lui; gli ingressi con date più vecchie sono di prima.
BACKFILL_DAYS = 90
# Più "ingressi" senza data registrati nello stesso istante sono un import in blocco, non operazioni vere.
IMPORT_BATCH_MIN_ENTRIES = 3


def _upgrade_9(conn: sqlite3.Connection) -> None:
    # Registro eventi (vedi db/event_log.py). member_id non è una chiave esterna: le righe devono restare
    # anche quando il membro viene eliminato, per questo il nome si copia nella riga.
    conn.executescript(
        """
        CREATE TABLE event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            at TEXT NOT NULL,
            kind TEXT NOT NULL,
            member_id INTEGER,
            member_name TEXT,
            from_status TEXT,
            to_status TEXT,
            detail TEXT
        );
        CREATE INDEX idx_event_log_at ON event_log(at);
        """
    )
    # Dallo storico che già c'è si recuperano gli eventi con data certa degli ultimi BACKFILL_DAYS giorni:
    # passaggi di lista, ingressi (con la data di ingresso, oppure registrati a mano nel momento in cui è
    # stato aggiunto il membro) e cambi di nome. Restano fuori gli "ingressi" di un import in blocco (tanti
    # nello stesso istante, senza data) e tutto ciò che non è mai stato registrato (modifiche ai dati,
    # eliminazioni). L'orario dei passaggi è in UTC (ora del database) e si converte in locale; le date senza
    # orario (00:00:00) restano com'erano.
    since = f"-{BACKFILL_DAYS} days"
    local = "CASE WHEN substr({c}, 12) = '00:00:00' THEN {c} ELSE datetime({c}, 'localtime') END"
    rows = conn.execute(
        f"""
        SELECT h.member_id, m.family_name, h.previous_status, h.new_status, h.note,
               {local.format(c='h.changed_at')} AS at
        FROM status_history h JOIN members m ON m.id = h.member_id
        WHERE h.changed_at IS NOT NULL AND date(h.changed_at) >= date('now', ?)
          AND (h.previous_status IS NOT NULL
               OR substr(h.changed_at, 12) = '00:00:00'
               OR (SELECT COUNT(*) FROM status_history x
                   WHERE x.previous_status IS NULL AND x.changed_at = h.changed_at) < ?)
        """,
        (since, IMPORT_BATCH_MIN_ENTRIES),
    ).fetchall()
    for row in rows:
        if row[2] is None:
            kind, detail = "added", None
        else:
            kind, detail = "status", ({"note": row[4]} if row[4] else None)
        conn.execute(
            "INSERT INTO event_log (at, kind, member_id, member_name, from_status, to_status, detail) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (row[5], kind, row[0], row[1], row[2], row[3], json.dumps(detail, ensure_ascii=False) if detail else None),
        )
    rows = conn.execute(
        f"""
        SELECT n.member_id, m.family_name, n.field, n.old_value, n.new_value,
               {local.format(c='n.changed_at')} AS at
        FROM name_history n JOIN members m ON m.id = n.member_id
        WHERE n.changed_at IS NOT NULL AND date(n.changed_at) >= date('now', ?)
        """,
        (since,),
    ).fetchall()
    for row in rows:
        detail = {"changes": [{"field": row[2], "old": row[3], "new": row[4]}]}
        conn.execute(
            "INSERT INTO event_log (at, kind, member_id, member_name, detail) VALUES (?, 'name', ?, ?, ?)",
            (row[5], row[0], row[1], json.dumps(detail, ensure_ascii=False)),
        )


MIGRATIONS = [
    _upgrade_1,
    _upgrade_2,
    _upgrade_3,
    _upgrade_4,
    _upgrade_5,
    _upgrade_6,
    _upgrade_7,
    _upgrade_8,
    _upgrade_9,
]


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
