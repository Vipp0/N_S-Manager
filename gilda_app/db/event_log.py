"""Registro eventi: cosa è stato fatto nel programma e quando (ingressi, uscite, cambi di nome, modifiche...).

Una riga per operazione, in ordine di tempo. Il nome del membro si copia nella riga al momento dell'evento:
così resta leggibile anche se poi il membro viene eliminato o rinominato. Il testo che si vede nella scheda
si costruisce all'apertura da tipo, liste e dettagli (vedi ui/event_log_page.py), non si salva già scritto:
cambiando la lingua del programma anche le righe vecchie seguono.

`detail` è un JSON, con chiavi diverse per tipo:
  added   {"joined": "yyyy-mm-dd"}               data di ingresso indicata, se diversa da oggi
  status  {"note": "..."}                        nota del movimento (es. motivo del ban)
  name    {"changes": [{"field", "old", "new"}]}
  edit    {"changes": [{"field", "old", "new"}]}
  history {"what": "status_entry" | "status_rebuilt" | "name_added" | "name_edited" | "name_deleted"}
  system  {"what": "import" | "reset" | "restore" | "backup", ...}   import: inserted, updated, skipped
"""
import json
import sqlite3
from datetime import datetime

KIND_ADDED = "added"
KIND_STATUS = "status"
KIND_NAME = "name"
KIND_EDIT = "edit"
KIND_DELETE = "delete"
KIND_HISTORY = "history"
KIND_SYSTEM = "system"

TONE_GOOD = "good"  # entra in gilda o torna membro attuale
TONE_BAD = "bad"  # esce dalla gilda (ex membro o bannato)
TONE_NEUTRAL = "neutral"

DEFAULT_LIMIT = 2000

_ACTIVE = "attivo"


def now_local() -> str:
    """Ora locale: nel registro l'orario si legge com'è sull'orologio di chi usa il programma."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_event(
    conn: sqlite3.Connection,
    kind: str,
    member_id: int | None = None,
    member_name: str | None = None,
    from_status: str | None = None,
    to_status: str | None = None,
    detail: dict | None = None,
    at: str | None = None,
    commit: bool = False,
) -> None:
    """Aggiunge una riga. Di norma non fa commit: la scrive nella stessa transazione dell'operazione che
    registra, che chiude con il proprio commit (o la annulla tutta)."""
    conn.execute(
        "INSERT INTO event_log (at, kind, member_id, member_name, from_status, to_status, detail) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            at or now_local(),
            kind,
            member_id,
            member_name,
            from_status,
            to_status,
            json.dumps(detail, ensure_ascii=False) if detail else None,
        ),
    )
    if commit:
        conn.commit()


def member_name(conn: sqlite3.Connection, member_id: int) -> str | None:
    row = conn.execute("SELECT family_name FROM members WHERE id = ?", (member_id,)).fetchone()
    return row["family_name"] if row else None


def get_events(conn: sqlite3.Connection, limit: int = DEFAULT_LIMIT) -> list[sqlite3.Row]:
    """Gli eventi più recenti per primi."""
    return conn.execute("SELECT * FROM event_log ORDER BY at DESC, id DESC LIMIT ?", (limit,)).fetchall()


def event_detail(row) -> dict:
    try:
        return json.loads(row["detail"]) if row["detail"] else {}
    except (TypeError, ValueError):
        return {}


def tone(row) -> str:
    """Colore dell'evento: verde chi entra o rientra tra i membri attuali, rosso chi esce (ex membro o
    bannato), neutro tutto il resto (modifiche, cambi di nome, passaggi tra ex membro e bannato...)."""
    kind, from_status, to_status = row["kind"], row["from_status"], row["to_status"]
    if kind == KIND_ADDED:
        return TONE_GOOD if to_status == _ACTIVE else TONE_NEUTRAL
    if kind == KIND_STATUS:
        if to_status == _ACTIVE:
            return TONE_GOOD
        if from_status == _ACTIVE:
            return TONE_BAD
    return TONE_NEUTRAL
