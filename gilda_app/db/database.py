import sqlite3
from pathlib import Path

from gilda_app.db.migrations import migrate
from gilda_app.models.member import Member


# Nomi di cui si registra lo storico dei cambi (colonne di members). Per tracciarne altri
# basta aggiungerli qui e prevederne l'etichetta ("label.<campo>") in i18n.
TRACKED_NAME_FIELDS = ("family_name",)


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    migrate(conn)
    return conn


def find_duplicate(conn: sqlite3.Connection, family_name: str, main_name: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM members WHERE family_name = ? AND IFNULL(main_name, '') = ?",
        (family_name, main_name or ""),
    ).fetchone()


def add_member(
    conn: sqlite3.Connection,
    family_name: str,
    main_name: str | None,
    discord_name: str | None,
    nations: list[str],
    status: str,
    data_inserimento: str | None = None,
    note: str | None = None,
    still_on_discord: bool = False,
    commit: bool = True,
    birthday: str | None = None,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO members (family_name, main_name, discord_name, status, data_inserimento, note, still_on_discord, birthday)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (family_name, main_name, discord_name, status, data_inserimento, note, int(still_on_discord), birthday),
    )
    member_id = cur.lastrowid
    for ord_idx, nation in enumerate(nations):
        conn.execute(
            "INSERT INTO member_nations (member_id, nation, ord) VALUES (?, ?, ?)",
            (member_id, nation, ord_idx),
        )
    # La nota generale del membro non è una nota sul movimento (quelle si aggiungono
    # spostando il membro, es. motivo del ban): qui lo storico resta senza nota.
    # changed_at riflette data_inserimento quando nota, altrimenti il momento attuale
    # (record storico/importato senza data nota).
    if data_inserimento:
        conn.execute(
            """
            INSERT INTO status_history (member_id, previous_status, new_status, changed_at, note)
            VALUES (?, NULL, ?, ?, NULL)
            """,
            (member_id, status, f"{data_inserimento} 00:00:00"),
        )
    else:
        conn.execute(
            """
            INSERT INTO status_history (member_id, previous_status, new_status, note)
            VALUES (?, NULL, ?, NULL)
            """,
            (member_id, status),
        )
    if commit:
        conn.commit()
    return member_id


def update_member(
    conn: sqlite3.Connection,
    member_id: int,
    family_name: str,
    main_name: str | None,
    discord_name: str | None,
    nations: list[str],
    note: str | None = None,
    data_inserimento: str | None = None,
    update_date: bool = False,
    still_on_discord: bool | None = None,
    commit: bool = True,
    record_name_changes: bool = False,
    update_birthday: bool = False,
    birthday: str | None = None,
) -> None:
    """update_date=False (default, usato dall'import) lascia invariato data_inserimento;
    update_date=True (usato dal form di modifica) lo imposta al valore passato, anche None.
    still_on_discord=None (default) lascia invariato il campo: il form lo mostra/modifica
    solo per gli ex membri, per tutti gli altri stati va lasciato così com'è.
    record_name_changes=True (form di modifica) registra nello storico nomi i cambi dei
    campi in TRACKED_NAME_FIELDS; l'import lo lascia False per non riempirlo di rumore.
    update_birthday=True (form di modifica) imposta il compleanno al valore passato, anche
    None; l'import lo lascia False per non cancellare quelli già inseriti."""
    if record_name_changes:
        old = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
        new_values = {"family_name": family_name}
        for field in TRACKED_NAME_FIELDS:
            if old is not None and old[field] and old[field] != new_values[field]:
                add_name_change(conn, member_id, field, old[field], new_values[field], commit=False)
    set_clauses = ["family_name = ?", "main_name = ?", "discord_name = ?", "note = ?"]
    params: list = [family_name, main_name, discord_name, note]
    if update_date:
        set_clauses.append("data_inserimento = ?")
        params.append(data_inserimento)
    if update_birthday:
        set_clauses.append("birthday = ?")
        params.append(birthday)
    if still_on_discord is not None:
        set_clauses.append("still_on_discord = ?")
        params.append(int(still_on_discord))
    set_clauses.append("updated_at = datetime('now')")
    params.append(member_id)
    conn.execute(f"UPDATE members SET {', '.join(set_clauses)} WHERE id = ?", params)

    if update_date:
        # Tiene sincronizzata la voce "ingresso" (previous_status NULL) dello storico
        # con la data corretta a mano nel form, così lo storico mostra sempre quella.
        changed_at = f"{data_inserimento} 00:00:00" if data_inserimento else None
        conn.execute(
            "UPDATE status_history SET changed_at = COALESCE(?, changed_at) "
            "WHERE member_id = ? AND previous_status IS NULL",
            (changed_at, member_id),
        )
    conn.execute("DELETE FROM member_nations WHERE member_id = ?", (member_id,))
    for ord_idx, nation in enumerate(nations):
        conn.execute(
            "INSERT INTO member_nations (member_id, nation, ord) VALUES (?, ?, ?)",
            (member_id, nation, ord_idx),
        )
    if commit:
        conn.commit()


def add_name_change(
    conn: sqlite3.Connection,
    member_id: int,
    field: str,
    old_value: str | None,
    new_value: str,
    date: str | None = None,
    commit: bool = True,
) -> None:
    """date (yyyy-mm-dd) None = adesso."""
    if date:
        conn.execute(
            "INSERT INTO name_history (member_id, field, old_value, new_value, changed_at) VALUES (?, ?, ?, ?, ?)",
            (member_id, field, old_value, new_value, f"{date} 00:00:00"),
        )
    else:
        conn.execute(
            "INSERT INTO name_history (member_id, field, old_value, new_value) VALUES (?, ?, ?, ?)",
            (member_id, field, old_value, new_value),
        )
    if commit:
        conn.commit()


def get_name_history(conn: sqlite3.Connection, member_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM name_history WHERE member_id = ? ORDER BY changed_at, id", (member_id,)
    ).fetchall()


def update_name_change(conn: sqlite3.Connection, entry_id: int, old_value: str | None, new_value: str, date: str) -> None:
    conn.execute(
        "UPDATE name_history SET old_value = ?, new_value = ?, changed_at = ? WHERE id = ?",
        (old_value, new_value, f"{date} 00:00:00", entry_id),
    )
    conn.commit()


def delete_name_change(conn: sqlite3.Connection, entry_id: int) -> None:
    conn.execute("DELETE FROM name_history WHERE id = ?", (entry_id,))
    conn.commit()


def old_names_by_member(conn: sqlite3.Connection) -> dict[int, list[str]]:
    """Vecchi nomi di ogni membro, per far trovare la persona anche cercando un nome che
    non usa più."""
    result: dict[int, list[str]] = {}
    for row in conn.execute("SELECT member_id, old_value FROM name_history WHERE IFNULL(old_value, '') != ''"):
        result.setdefault(row["member_id"], []).append(row["old_value"])
    return result


def delete_member(conn: sqlite3.Connection, member_id: int) -> None:
    conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
    conn.commit()


def move_member_status(
    conn: sqlite3.Connection,
    member_id: int,
    new_status: str,
    note: str | None = None,
    still_on_discord: bool | None = None,
) -> None:
    """still_on_discord=None lascia invariato il campo; usato solo quando si sposta
    verso ex membro, per registrare se la persona resta nel canale Discord della
    gilda pur avendo lasciato la gilda in gioco."""
    row = conn.execute("SELECT status FROM members WHERE id = ?", (member_id,)).fetchone()
    if row is None:
        return
    previous_status = row["status"]
    if still_on_discord is None:
        conn.execute(
            "UPDATE members SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (new_status, member_id),
        )
    else:
        conn.execute(
            "UPDATE members SET status = ?, still_on_discord = ?, updated_at = datetime('now') WHERE id = ?",
            (new_status, int(still_on_discord), member_id),
        )
    conn.execute(
        """
        INSERT INTO status_history (member_id, previous_status, new_status, note)
        VALUES (?, ?, ?, ?)
        """,
        (member_id, previous_status, new_status, note),
    )
    conn.commit()


def get_members(conn: sqlite3.Connection, status: str) -> list[Member]:
    rows = conn.execute(
        "SELECT * FROM members WHERE status = ? ORDER BY family_name COLLATE NOCASE",
        (status,),
    ).fetchall()
    members = []
    for row in rows:
        nations = [
            r["nation"]
            for r in conn.execute(
                "SELECT nation FROM member_nations WHERE member_id = ? ORDER BY ord", (row["id"],)
            ).fetchall()
        ]
        members.append(
            Member(
                id=row["id"],
                family_name=row["family_name"],
                main_name=row["main_name"] or "",
                discord_name=row["discord_name"] or "",
                status=row["status"],
                data_inserimento=row["data_inserimento"],
                note=row["note"],
                nations=nations,
                still_on_discord=bool(row["still_on_discord"]),
                birthday=row["birthday"],
            )
        )
    return members


def get_status_history(conn: sqlite3.Connection, member_id: int) -> list[sqlite3.Row]:
    """In ordine di registrazione (id), che coincide con la catena dei passaggi: con le date
    sconosciute l'ordine cronologico non si può ricavare dalle date."""
    return conn.execute(
        "SELECT * FROM status_history WHERE member_id = ? ORDER BY id", (member_id,)
    ).fetchall()


def update_status_history_entry(conn: sqlite3.Connection, history_id: int, date: str | None, note: str | None) -> None:
    """Corregge data/nota di una voce di storico già registrata (es. per inserire a
    posteriori una data reale al posto di quella automatica). Se la voce corretta è
    quella di ingresso (previous_status NULL), sincronizza anche members.data_inserimento,
    che resta la fonte usata per la hall of fame."""
    row = conn.execute(
        "SELECT member_id, previous_status FROM status_history WHERE id = ?", (history_id,)
    ).fetchone()
    if row is None:
        return
    conn.execute(
        "UPDATE status_history SET changed_at = ?, note = ? WHERE id = ?",
        (f"{date} 00:00:00" if date else None, note, history_id),
    )
    if row["previous_status"] is None:
        conn.execute("UPDATE members SET data_inserimento = ? WHERE id = ?", (date, row["member_id"]))
    conn.commit()


def rebuild_status_history(conn: sqlite3.Connection, member_id: int, entries: list[dict]) -> None:
    """Sostituisce tutto lo storico movimenti di un membro con la sequenza passata
    (ordinata cronologicamente da chi chiama), es. per inserire a posteriori lo storico
    di un membro già esistente dopo un import. Aggiorna anche members.status e
    data_inserimento in modo che i comandi normali (sposta, correggi voce) proseguano
    da qui in avanti esattamente come se lo storico fosse stato costruito passo passo.
    entries: lista di {"status", "date" (yyyy-mm-dd o None se sconosciuta), "note"}, non
    vuota, nell'ordine in cui i passaggi sono avvenuti."""
    conn.execute("DELETE FROM status_history WHERE member_id = ?", (member_id,))
    previous_status = None
    for entry in entries:
        conn.execute(
            """
            INSERT INTO status_history (member_id, previous_status, new_status, changed_at, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                member_id,
                previous_status,
                entry["status"],
                f"{entry['date']} 00:00:00" if entry["date"] else None,
                entry["note"],
            ),
        )
        previous_status = entry["status"]
    conn.execute(
        "UPDATE members SET status = ?, data_inserimento = ?, updated_at = datetime('now') WHERE id = ?",
        (entries[-1]["status"], entries[0]["date"], member_id),
    )
    conn.commit()


def reset_database(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM status_history")
    conn.execute("DELETE FROM name_history")
    conn.execute("DELETE FROM member_nations")
    conn.execute("DELETE FROM members")
    conn.execute(
        "DELETE FROM sqlite_sequence WHERE name IN ('members', 'member_nations', 'status_history', 'name_history')"
    )
    conn.commit()


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def delete_setting(conn: sqlite3.Connection, key: str) -> None:
    """Rimuove un'impostazione e riscrive il file: senza VACUUM SQLite lascia il vecchio
    valore leggibile nelle pagine libere del database (pensato per le chiavi API, da
    poter togliere prima di dare il database a qualcun altro)."""
    conn.execute("DELETE FROM app_settings WHERE key = ?", (key,))
    conn.commit()
    conn.execute("VACUUM")


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO app_settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
