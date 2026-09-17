import sqlite3
from pathlib import Path

from gilda_app.db.migrations import migrate
from gilda_app.models.member import Member


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
    commit: bool = True,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO members (family_name, main_name, discord_name, status, data_inserimento, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (family_name, main_name, discord_name, status, data_inserimento, note),
    )
    member_id = cur.lastrowid
    for ord_idx, nation in enumerate(nations):
        conn.execute(
            "INSERT INTO member_nations (member_id, nation, ord) VALUES (?, ?, ?)",
            (member_id, nation, ord_idx),
        )
    conn.execute(
        """
        INSERT INTO status_history (member_id, previous_status, new_status, note)
        VALUES (?, NULL, ?, ?)
        """,
        (member_id, status, note),
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
    commit: bool = True,
) -> None:
    """update_date=False (default, usato dall'import) lascia invariato data_inserimento;
    update_date=True (usato dal form di modifica) lo imposta al valore passato, anche None."""
    if update_date:
        conn.execute(
            """
            UPDATE members
            SET family_name = ?, main_name = ?, discord_name = ?, note = ?,
                data_inserimento = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (family_name, main_name, discord_name, note, data_inserimento, member_id),
        )
    else:
        conn.execute(
            """
            UPDATE members
            SET family_name = ?, main_name = ?, discord_name = ?, note = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (family_name, main_name, discord_name, note, member_id),
        )
    conn.execute("DELETE FROM member_nations WHERE member_id = ?", (member_id,))
    for ord_idx, nation in enumerate(nations):
        conn.execute(
            "INSERT INTO member_nations (member_id, nation, ord) VALUES (?, ?, ?)",
            (member_id, nation, ord_idx),
        )
    if commit:
        conn.commit()


def delete_member(conn: sqlite3.Connection, member_id: int) -> None:
    conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
    conn.commit()


def move_member_status(conn: sqlite3.Connection, member_id: int, new_status: str, note: str | None = None) -> None:
    row = conn.execute("SELECT status FROM members WHERE id = ?", (member_id,)).fetchone()
    if row is None:
        return
    previous_status = row["status"]
    conn.execute(
        "UPDATE members SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (new_status, member_id),
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
            )
        )
    return members


def get_status_history(conn: sqlite3.Connection, member_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM status_history WHERE member_id = ? ORDER BY changed_at", (member_id,)
    ).fetchall()


def reset_database(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM status_history")
    conn.execute("DELETE FROM member_nations")
    conn.execute("DELETE FROM members")
    conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('members', 'member_nations', 'status_history')")
    conn.commit()


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO app_settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
