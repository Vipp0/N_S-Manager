"""Formattazione testuale di una riga di status_history, condivisa tra il form
membro e il dialog di correzione di una singola voce di storico."""
from gilda_app.i18n import tr
from gilda_app.models.member import STATUS_ATTIVO, STATUS_EX_MEMBRO, status_label


def format_history_line(row) -> str:
    date = row["changed_at"][:10]
    if row["previous_status"] is None:
        line = tr("history.joined", date=date, status=status_label(row["new_status"]))
    elif row["previous_status"] == STATUS_EX_MEMBRO and row["new_status"] == STATUS_ATTIVO:
        line = tr("history.rejoined", date=date)
    else:
        line = tr(
            "history.transition",
            date=date,
            prev=status_label(row["previous_status"]),
            new=status_label(row["new_status"]),
        )
    if row["note"]:
        line += tr("history.note_suffix", note=row["note"])
    return line
