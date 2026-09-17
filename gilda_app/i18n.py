"""Sistema di traduzione minimale per l'interfaccia (italiano/inglese).

Il cambio lingua richiede il riavvio dell'app: tutte le stringhe passano da tr(),
letto una volta all'avvio in base alla preferenza salvata nel database."""

DEFAULT_LANGUAGE = "it"
LANGUAGES = {"it": "Italiano", "en": "English"}

_current_language = DEFAULT_LANGUAGE

STRINGS: dict[str, dict[str, str]] = {
    # -- Stati membro --------------------------------------------------
    "status.attivo": {"it": "Membri attuali", "en": "Current members"},
    "status.ex_membro": {"it": "Ex membri", "en": "Former members"},
    "status.bannato": {"it": "Bannati", "en": "Banned"},

    # -- Finestra principale / navigazione ------------------------------
    "window.title": {"it": "Gestionale Membri Gilda", "en": "Guild Members Manager"},
    "nav.stats": {"it": "Statistiche", "en": "Statistics"},
    "nav.settings": {"it": "Impostazioni", "en": "Settings"},

    # -- Import iniziale (primo avvio) ------------------------------------
    "dialog.initial_import.title": {"it": "Importazione iniziale", "en": "Initial import"},
    "dialog.initial_import.body": {
        "it": 'Il database è vuoto. Importare i dati da "{filename}" trovato nella cartella?',
        "en": 'The database is empty. Import data from "{filename}" found in the folder?',
    },
    "dialog.initial_import_done.title": {"it": "Import completato", "en": "Import complete"},
    "import.sheet_line": {
        "it": "{sheet}: {imported} righe importate, {skipped} scartate",
        "en": "{sheet}: {imported} rows imported, {skipped} skipped",
    },
    "import.duplicates_skipped": {
        "it": "\nDuplicati incrociati saltati: {count}",
        "en": "\nCross-sheet duplicates skipped: {count}",
    },

    # -- Tabella membri --------------------------------------------------
    "column.number": {"it": "N.", "en": "No."},
    "column.family_name": {"it": "Family Name", "en": "Family Name"},
    "column.main_name": {"it": "Main Name", "en": "Main Name"},
    "column.nation": {"it": "Nazione", "en": "Nation"},
    "column.discord_name": {"it": "Discord Name", "en": "Discord Name"},
    "column.note": {"it": "Note", "en": "Notes"},
    "search.placeholder": {"it": "Cerca per nome, nazione, discord...", "en": "Search by name, nation, discord..."},
    "button.add_member": {"it": "Aggiungi membro", "en": "Add member"},
    "menu.copy_row": {"it": "Copia riga", "en": "Copy row"},
    "menu.copy_field": {"it": "Copia {field}", "en": "Copy {field}"},
    "menu.edit": {"it": "Modifica", "en": "Edit"},
    "menu.move": {"it": "Sposta in un'altra lista", "en": "Move to another list"},
    "menu.delete": {"it": "Elimina", "en": "Delete"},

    # -- Form membro ------------------------------------------------------
    "dialog.edit_member.title": {"it": "Modifica membro", "en": "Edit member"},
    "dialog.new_member.title": {"it": "Nuovo membro", "en": "New member"},
    "field.family_name.placeholder": {"it": "Family Name (obbligatorio)", "en": "Family Name (required)"},
    "field.main_name.placeholder": {"it": "Main Name", "en": "Main Name"},
    "field.discord_name.placeholder": {"it": "Discord Name", "en": "Discord Name"},
    "field.nation1.placeholder": {"it": "Nazione", "en": "Nation"},
    "field.nation2.placeholder": {"it": "Seconda nazione (opzionale)", "en": "Second nation (optional)"},
    "field.date_check": {"it": "Registra la data di ingresso in gilda", "en": "Record the guild join date"},
    "field.note.placeholder": {"it": "Note", "en": "Notes"},
    "label.family_name": {"it": "Family Name", "en": "Family Name"},
    "label.main_name": {"it": "Main Name", "en": "Main Name"},
    "label.discord_name": {"it": "Discord Name", "en": "Discord Name"},
    "label.nation1": {"it": "Nazione 1", "en": "Nation 1"},
    "label.nation2": {"it": "Nazione 2", "en": "Nation 2"},
    "label.note": {"it": "Note", "en": "Notes"},
    "error.family_name_required": {"it": "Family Name è obbligatorio.", "en": "Family Name is required."},
    "button.save": {"it": "Salva", "en": "Save"},
    "button.cancel": {"it": "Annulla", "en": "Cancel"},

    # -- Spostamento tra liste --------------------------------------------
    "dialog.move.title": {"it": "Sposta {name}", "en": "Move {name}"},
    "dialog.move.current_list": {"it": "Lista attuale: {status}", "en": "Current list: {status}"},
    "dialog.move.target_label": {"it": "Sposta in:", "en": "Move to:"},
    "dialog.move.note_label": {"it": "Nota (opzionale, es. motivo del ban):", "en": "Note (optional, e.g. ban reason):"},
    "button.confirm_move": {"it": "Conferma spostamento", "en": "Confirm move"},

    # -- Elimina membro -----------------------------------------------------
    "dialog.delete.title": {"it": "Elimina membro", "en": "Delete member"},
    "dialog.delete.body": {
        "it": "Eliminare definitivamente {name} ({main})? L'azione non è reversibile.",
        "en": "Permanently delete {name} ({main})? This action cannot be undone.",
    },

    # -- Impostazioni --------------------------------------------------------
    "settings.title": {"it": "Impostazioni", "en": "Settings"},
    "settings.language_label": {"it": "Lingua", "en": "Language"},
    "dialog.restart.title": {"it": "Riavvia l'applicazione", "en": "Restart the application"},
    "dialog.restart.body": {
        "it": "Per applicare la nuova lingua è necessario riavviare l'applicazione. Vuoi riavviarla adesso?",
        "en": "Restarting the application is required to apply the new language. Do you want to restart now?",
    },
    "button.restart_now": {"it": "Riavvia ora", "en": "Restart now"},
    "button.later": {"it": "Più tardi", "en": "Later"},
    "settings.import": {"it": "Importa da Excel...", "en": "Import from Excel..."},
    "settings.export": {"it": "Esporta in Excel...", "en": "Export to Excel..."},
    "settings.reset": {"it": "Azzera database", "en": "Reset database"},

    # -- Import ------------------------------------------------------------
    "dialog.import_preview.title": {"it": "Anteprima import", "en": "Import preview"},
    "import.sheet_summary": {
        "it": "{sheet} → {status}: {imported} righe valide, {skipped} righe vuote scartate",
        "en": "{sheet} → {status}: {imported} valid rows, {skipped} blank rows skipped",
    },
    "import.total_rows": {"it": "\nTotale righe da importare: {total}", "en": "\nTotal rows to import: {total}"},
    "import.duplicate_warning": {
        "it": "⚠ {count} nominativi risultano già presenti nel database (stesso Family Name + Main Name). Cosa vuoi fare con questi duplicati?",
        "en": "⚠ {count} names are already present in the database (same Family Name + Main Name). What do you want to do with these duplicates?",
    },
    "import.policy_skip": {"it": "Salta i duplicati (non modificarli)", "en": "Skip duplicates (don't modify them)"},
    "import.policy_update": {
        "it": "Aggiorna i duplicati esistenti con i nuovi dati",
        "en": "Update existing duplicates with the new data",
    },
    "import.policy_insert": {
        "it": "Inserisci comunque come nuove voci separate",
        "en": "Insert anyway as separate new entries",
    },
    "button.confirm_import": {"it": "Conferma import", "en": "Confirm import"},
    "progress.import_title": {"it": "Importazione in corso...", "en": "Import in progress..."},
    "progress.import_preparing": {"it": "Preparazione...", "en": "Preparing..."},
    "progress.import_status": {"it": "Importazione in corso... {current}/{total} righe", "en": "Importing... {current}/{total} rows"},
    "notify.import_done.title": {"it": "Import completato", "en": "Import complete"},
    "notify.import_done.body": {
        "it": "Inseriti: {inserted} · Aggiornati: {updated} · Saltati: {skipped}",
        "en": "Inserted: {inserted} · Updated: {updated} · Skipped: {skipped}",
    },
    "notify.import_failed.title": {"it": "Import fallito", "en": "Import failed"},
    "notify.import_failed.body": {"it": "Impossibile leggere il file: {error}", "en": "Could not read the file: {error}"},
    "dialog.pick_import_file": {"it": "Seleziona file Excel da importare", "en": "Select Excel file to import"},

    # -- Export --------------------------------------------------------------
    "dialog.pick_export_file": {"it": "Esporta in Excel", "en": "Export to Excel"},
    "notify.export_done.title": {"it": "Export completato", "en": "Export complete"},
    "notify.export_done.body": {"it": "File salvato in {path}", "en": "File saved to {path}"},
    "notify.export_failed.title": {"it": "Export fallito", "en": "Export failed"},

    # -- Azzeramento database --------------------------------------------------
    "dialog.reset_warn.title": {"it": "Azzera database", "en": "Reset database"},
    "dialog.reset_warn.body": {
        "it": "Stai per eliminare TUTTI i membri e lo storico movimenti. Questa è la prima delle due conferme richieste.",
        "en": "You're about to delete ALL members and the movement history. This is the first of two required confirmations.",
    },
    "dialog.reset_confirm.title": {"it": "Conferma azzeramento database", "en": "Confirm database reset"},
    "dialog.reset_confirm.body": {
        "it": "Questa azione elimina definitivamente TUTTI i membri e lo storico movimenti.\nVerrà comunque creato un backup automatico prima di procedere.\n\nPer confermare, digita \"{word}\" qui sotto:",
        "en": "This action permanently deletes ALL members and the movement history.\nAn automatic backup will still be created before proceeding.\n\nTo confirm, type \"{word}\" below:",
    },
    "dialog.reset_confirm.error": {
        "it": "Devi digitare esattamente \"{word}\" per confermare.",
        "en": "You must type exactly \"{word}\" to confirm.",
    },
    "button.confirm_reset": {"it": "Azzera definitivamente", "en": "Permanently reset"},
    "notify.reset_done.title": {"it": "Database azzerato", "en": "Database reset"},
    "notify.reset_done.body": {
        "it": "Tutti i dati sono stati eliminati. Backup salvato in backups/.",
        "en": "All data has been deleted. Backup saved in backups/.",
    },

    # -- Notifiche CRUD ------------------------------------------------------
    "notify.member_added.title": {"it": "Membro aggiunto", "en": "Member added"},
    "notify.member_added.body": {"it": "{name} aggiunto a {status}.", "en": "{name} added to {status}."},
    "notify.member_updated.title": {"it": "Membro aggiornato", "en": "Member updated"},
    "notify.member_updated.body": {"it": "{name} è stato aggiornato.", "en": "{name} has been updated."},
    "notify.member_deleted.title": {"it": "Membro eliminato", "en": "Member deleted"},
    "notify.member_deleted.body": {"it": "{name} è stato eliminato.", "en": "{name} has been deleted."},
    "notify.member_moved.title": {"it": "Membro spostato", "en": "Member moved"},
    "notify.member_moved.body": {"it": "{name} spostato in {status}.", "en": "{name} moved to {status}."},

    # -- Statistiche -----------------------------------------------------------
    "stats.title": {"it": "Statistiche", "en": "Statistics"},
    "stats.current_members": {"it": "Membri attuali", "en": "Current members"},
    "stats.former_members": {"it": "Ex membri", "en": "Former members"},
    "stats.banned": {"it": "Bannati", "en": "Banned"},
    "stats.total_history": {"it": "Totale storico", "en": "Total history"},
    "stats.avg_tenure": {"it": "Permanenza media prima di uscire", "en": "Average tenure before leaving"},
    "stats.avg_tenure_days": {"it": "{days:.0f} giorni", "en": "{days:.0f} days"},
    "stats.avg_tenure_unknown": {"it": "n/d", "en": "n/a"},
    "stats.rejoin_rate": {"it": "Tasso di rientro", "en": "Rejoin rate"},
    "stats.recent_changes": {"it": "Movimenti ultimi 30 giorni", "en": "Movements in the last 30 days"},
    "stats.trend_chart": {"it": "Andamento membri attivi nel tempo", "en": "Active members trend over time"},
    "stats.nation_chart": {
        "it": "Distribuzione per nazione (membri attuali, top 10)",
        "en": "Distribution by nation (current members, top 10)",
    },
    "stats.top_rejoiners": {"it": "Membri con più rientri", "en": "Members with the most rejoins"},
    "stats.top_rejoiners_line": {"it": "{name} ({main}) — {count} rientri", "en": "{name} ({main}) — {count} rejoins"},
    "stats.ban_reasons": {"it": "Motivi di ban più comuni", "en": "Most common ban reasons"},
    "stats.ban_reasons_line": {"it": "{reason} — {count} casi", "en": "{reason} — {count} cases"},
    "stats.hall_of_fame": {"it": "Hall of fame (membri attuali più anziani)", "en": "Hall of fame (longest-standing current members)"},
    "stats.hall_of_fame_line": {"it": "{name} ({main}) — dal {since}", "en": "{name} ({main}) — since {since}"},
    "stats.no_data": {"it": "Nessun dato disponibile.", "en": "No data available."},
}


def set_language(lang: str) -> None:
    global _current_language
    _current_language = lang if lang in LANGUAGES else DEFAULT_LANGUAGE


def get_language() -> str:
    return _current_language


def tr(key: str, **kwargs) -> str:
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(_current_language, entry.get(DEFAULT_LANGUAGE, key))
    return text.format(**kwargs) if kwargs else text
