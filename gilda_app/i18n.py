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
    "window.title": {"it": "Night_Shade Manager", "en": "Night_Shade Manager"},
    "nav.stats": {"it": "Statistiche", "en": "Statistics"},
    "nav.notes": {"it": "Note", "en": "Notes"},
    "nav.calendar": {"it": "Calendario", "en": "Calendar"},
    "nav.settings": {"it": "Impostazioni", "en": "Settings"},

    # -- Import iniziale (primo avvio) ------------------------------------
    "dialog.initial_import.title": {"it": "Importazione iniziale", "en": "Initial import"},
    "dialog.initial_import.body": {
        "it": 'Il database è vuoto. Importare i dati da "{filename}" trovato nella cartella?',
        "en": 'The database is empty. Import data from "{filename}" found in the folder?',
    },

    # -- Tabella membri --------------------------------------------------
    "column.number": {"it": "N.", "en": "No."},
    "column.family_name": {"it": "Family Name", "en": "Family Name"},
    "column.main_name": {"it": "Main Name", "en": "Main Name"},
    "column.nation": {"it": "Nazione", "en": "Nation"},
    "column.discord_name": {"it": "Discord Name", "en": "Discord Name"},
    "column.still_on_discord": {"it": "Still on Discord", "en": "Still on Discord"},
    "column.note": {"it": "Note", "en": "Notes"},
    "nation.unknown": {"it": "Sconosciuta", "en": "Unknown"},
    "search.placeholder": {"it": "Cerca per nome, nazione, discord...", "en": "Search by name, nation, discord..."},
    "button.add_member": {"it": "Aggiungi membro", "en": "Add member"},
    "menu.copy_row": {"it": "Copia riga", "en": "Copy row"},
    "menu.copy_field": {"it": "Copia {field}", "en": "Copy {field}"},
    "menu.copy_discord": {"it": "Copia per Discord", "en": "Copy for Discord"},
    "menu.edit": {"it": "Modifica", "en": "Edit"},
    "menu.move": {"it": "Sposta in un'altra lista", "en": "Move to another list"},
    "menu.delete": {"it": "Elimina", "en": "Delete"},

    # -- Ricerca globale (tutte e 3 le schede) -----------------------------
    "search.global.tooltip": {"it": "Cerca in tutte le liste", "en": "Search across all lists"},
    "search.global.title": {"it": "Cerca in tutte le liste", "en": "Search across all lists"},
    "search.global.placeholder": {
        "it": "Cerca per nome, nazione, discord in Attuali, Ex membri e Bannati...",
        "en": "Search by name, nation, discord across Current, Former and Banned...",
    },
    "search.global.column.status": {"it": "Lista", "en": "List"},
    "search.global.go": {"it": "Vai al membro", "en": "Go to member"},

    # -- Form membro ------------------------------------------------------
    "dialog.edit_member.title": {"it": "Modifica membro", "en": "Edit member"},
    "dialog.new_member.title": {"it": "Nuovo membro", "en": "New member"},
    "field.family_name.placeholder": {"it": "Family Name (obbligatorio)", "en": "Family Name (required)"},
    "field.main_name.placeholder": {"it": "Main Name", "en": "Main Name"},
    "field.discord_name.placeholder": {"it": "Discord Name", "en": "Discord Name"},
    "field.nation1.placeholder": {"it": "Nazione", "en": "Nation"},
    "field.nation2.placeholder": {"it": "Seconda nazione (opzionale)", "en": "Second nation (optional)"},
    "field.date_check": {"it": "Registra la data di ingresso in gilda", "en": "Record the guild join date"},
    "field.still_on_discord": {
        "it": "È ancora presente nel canale Discord della gilda",
        "en": "Still present in the guild's Discord channel",
    },
    "field.note.placeholder": {"it": "Note", "en": "Notes"},
    "label.list": {"it": "Lista", "en": "List"},
    "label.family_name": {"it": "Family Name", "en": "Family Name"},
    "label.main_name": {"it": "Main Name", "en": "Main Name"},
    "label.discord_name": {"it": "Discord Name", "en": "Discord Name"},
    "label.nation1": {"it": "Nazione 1", "en": "Nation 1"},
    "label.nation2": {"it": "Nazione 2", "en": "Nation 2"},
    "label.note": {"it": "Note", "en": "Notes"},
    "label.history": {"it": "Storico movimenti", "en": "Movement history"},
    "history.joined": {"it": "{date} — Ingresso in gilda ({status})", "en": "{date} — Joined the guild ({status})"},
    "history.rejoined": {"it": "{date} — Rientro in gilda", "en": "{date} — Rejoined the guild"},
    "history.transition": {"it": "{date} — {prev} → {new}", "en": "{date} — {prev} → {new}"},
    "history.note_suffix": {"it": " — nota: {note}", "en": " — note: {note}"},
    "history.empty": {"it": "Nessuno storico movimenti.", "en": "No movement history."},
    "history.hint": {"it": "Doppio click su una voce per correggerne data o nota.", "en": "Double-click an entry to correct its date or note."},
    "label.date": {"it": "Data", "en": "Date"},
    "dialog.edit_history.title": {"it": "Correggi voce storico", "en": "Correct history entry"},
    "button.rebuild_history": {"it": "Ricostruisci storico...", "en": "Rebuild history..."},
    "dialog.rebuild_history.title": {"it": "Ricostruisci storico di {name}", "en": "Rebuild history of {name}"},
    "dialog.rebuild_history.hint": {
        "it": "Inserisci in ordine tutti i passaggi già avvenuti (es. entrato, uscito, rientrato...), "
        "ognuno con la sua data: verranno ordinati automaticamente e sostituiranno l'intero storico "
        "attuale di questo membro. Da qui in avanti si continua a tracciare come sempre.",
        "en": "Enter every past change (e.g. joined, left, rejoined...) with its date: they'll be "
        "sorted automatically and will replace this member's entire current history. "
        "From here on, tracking continues as usual.",
    },
    "dialog.rebuild_history.add_row": {"it": "Aggiungi passaggio", "en": "Add step"},
    "dialog.rebuild_history.error_same_status": {
        "it": "Due passaggi consecutivi non possono avere la stessa lista: correggi le date o le liste scelte.",
        "en": "Two consecutive steps can't have the same list: fix the dates or the lists chosen.",
    },
    "error.family_name_required": {"it": "Family Name è obbligatorio.", "en": "Family Name is required."},
    "button.save": {"it": "Salva", "en": "Save"},
    "button.cancel": {"it": "Annulla", "en": "Cancel"},
    "button.close": {"it": "Chiudi", "en": "Close"},

    # -- Spostamento tra liste --------------------------------------------
    "dialog.move.title": {"it": "Sposta {name}", "en": "Move {name}"},
    "dialog.move.current_list": {"it": "Lista attuale: {status}", "en": "Current list: {status}"},
    "dialog.move.target_label": {"it": "Sposta in:", "en": "Move to:"},
    "dialog.move.note_label": {"it": "Nota (opzionale, es. motivo del ban):", "en": "Note (optional, e.g. ban reason):"},
    "dialog.move.still_on_discord": {
        "it": "L'utente rimarrà nel canale Discord della gilda?",
        "en": "Will the member stay in the guild's Discord channel?",
    },
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
    "update.available.title": {"it": "Aggiornamento disponibile", "en": "Update available"},
    "update.available.body": {
        "it": "È disponibile la versione {version}. Vuoi aprire la pagina per scaricarla?",
        "en": "Version {version} is available. Do you want to open the download page?",
    },
    "update.available.open": {"it": "Apri pagina", "en": "Open page"},
    "settings.import": {"it": "Importa da Excel...", "en": "Import from Excel..."},
    "settings.export": {"it": "Esporta in Excel...", "en": "Export to Excel..."},
    "settings.reset": {"it": "Azzera database", "en": "Reset database"},
    "settings.version": {"it": "Night_Shade Manager — versione {version}", "en": "Night_Shade Manager — version {version}"},
    "settings.changelog": {"it": "Changelog", "en": "Changelog"},
    "settings.changelog_button": {"it": "Storico modifiche (changelog)", "en": "Version history (changelog)"},

    # -- Backup --------------------------------------------------------------
    "backup.title": {"it": "Backup", "en": "Backup"},
    "backup.hint": {
        "it": "Ogni giorno, all'apertura del programma, viene salvata una copia automatica (ne restano le ultime 30). "
        "Altre copie si creano prima di spostamenti, import e azzeramenti.",
        "en": "Once a day, when the program starts, an automatic copy is saved (the latest 30 are kept). "
        "More copies are made before moves, imports and resets.",
    },
    "backup.create_now": {"it": "Crea backup ora", "en": "Back up now"},
    "backup.open_folder": {"it": "Apri cartella backup", "en": "Open backup folder"},
    "backup.restore": {"it": "Ripristina da backup...", "en": "Restore from backup..."},
    "backup.extra_label": {"it": "Seconda copia in un'altra posizione (es. un altro disco)", "en": "Second copy in another location (e.g. another disk)"},
    "backup.extra_none": {"it": "Nessuna: i backup restano solo nella cartella del programma", "en": "None: backups stay only in the program folder"},
    "backup.extra_choose": {"it": "Scegli cartella...", "en": "Choose folder..."},
    "backup.extra_remove": {"it": "Rimuovi", "en": "Remove"},
    "backup.pick_extra_dir": {"it": "Scegli la cartella per la seconda copia dei backup", "en": "Choose the folder for the second copy of backups"},
    "backup.reason.auto": {"it": "automatico", "en": "automatic"},
    "backup.reason.manual": {"it": "manuale", "en": "manual"},
    "backup.reason.move": {"it": "prima di uno spostamento", "en": "before a move"},
    "backup.reason.import": {"it": "prima di un import", "en": "before an import"},
    "backup.reason.reset": {"it": "prima di un azzeramento", "en": "before a reset"},
    "backup.reason.pre-restore": {"it": "prima di un ripristino", "en": "before a restore"},
    "backup.notify.created.title": {"it": "Backup creato", "en": "Backup created"},
    "backup.notify.created.body": {"it": "Salvato come {name}", "en": "Saved as {name}"},
    "backup.notify.extra_failed.title": {"it": "Seconda copia non riuscita", "en": "Second copy failed"},
    "backup.notify.extra_failed.body": {
        "it": "Il backup principale è stato salvato, ma non la copia nell'altra posizione: {error}",
        "en": "The main backup was saved, but not the copy in the other location: {error}",
    },
    "backup.notify.extra_set.title": {"it": "Seconda copia attiva", "en": "Second copy enabled"},
    "backup.notify.extra_set.body": {"it": "I prossimi backup saranno copiati anche in {path}", "en": "Next backups will also be copied to {path}"},
    "backup.notify.extra_bad.title": {"it": "Cartella non utilizzabile", "en": "Folder not usable"},
    "backup.notify.extra_bad.body": {"it": "Non riesco a scrivere in quella cartella: {error}", "en": "Cannot write to that folder: {error}"},
    "backup.notify.extra_removed.title": {"it": "Seconda copia disattivata", "en": "Second copy disabled"},
    "backup.notify.extra_removed.body": {"it": "I backup restano solo nella cartella del programma.", "en": "Backups now stay only in the program folder."},
    "backup.notify.restore_failed.title": {"it": "Ripristino non riuscito", "en": "Restore failed"},
    "backup.notify.restore_failed.body": {"it": "Il database attuale non è stato modificato: {error}", "en": "The current database was not changed: {error}"},
    "backup.restore.title": {"it": "Ripristina da backup", "en": "Restore from backup"},
    "backup.restore.hint": {
        "it": "Scegli il backup da ripristinare. Prima del ripristino viene salvata una copia dello stato attuale, poi il programma si riavvia.",
        "en": "Choose the backup to restore. A copy of the current state is saved first, then the program restarts.",
    },
    "backup.restore.empty": {"it": "Non ci sono ancora backup.", "en": "There are no backups yet."},
    "backup.restore.button": {"it": "Ripristina", "en": "Restore"},
    "backup.restore.confirm.title": {"it": "Confermi il ripristino?", "en": "Confirm restore?"},
    "backup.restore.confirm.body": {
        "it": "I dati attuali verranno sostituiti con quelli del backup del {when}. "
        "Una copia dello stato attuale viene salvata prima, poi il programma si riavvia.",
        "en": "Current data will be replaced with the backup from {when}. "
        "A copy of the current state is saved first, then the program restarts.",
    },
    "backup.restore.invalid": {"it": "Questo file non è un backup valido.", "en": "This file is not a valid backup."},

    # -- Import ------------------------------------------------------------
    "dialog.import_preview.title": {"it": "Anteprima import", "en": "Import preview"},
    "import.sheet_summary": {
        "it": "{sheet} → {status}: {imported} righe valide, {skipped} righe vuote scartate",
        "en": "{sheet} → {status}: {imported} valid rows, {skipped} blank rows skipped",
    },
    "import.total_rows": {"it": "\nTotale righe da importare: {total}", "en": "\nTotal rows to import: {total}"},
    "import.intra_duplicate_warning": {
        "it": "\n⚠ {count} nominativi compaiono più volte nel file stesso (stesso Family Name + Main Name):",
        "en": "\n⚠ {count} names appear more than once within the file itself (same Family Name + Main Name):",
    },
    "import.intra_duplicate_line": {
        "it": "  {family} {main} — {sheet1} riga {row1} → {sheet2} riga {row2}",
        "en": "  {family} {main} — {sheet1} row {row1} → {sheet2} row {row2}",
    },
    "import.intra_duplicate_fields_differ": {
        "it": "(nazione o discord diversi tra le due righe: controlla)",
        "en": "(nation or discord differ between the two rows: check)",
    },
    "import.intra_duplicate_more": {"it": "  ... e altri {count}", "en": "  ... and {count} more"},
    "import.duplicate_warning": {
        "it": "\n⚠ In totale {count} duplicati (nel database e/o nel file). Cosa vuoi fare con questi duplicati?",
        "en": "\n⚠ {count} duplicates in total (in the database and/or in the file). What do you want to do with these duplicates?",
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
    "notify.member_added.body_clipboard": {
        "it": "{name} aggiunto a {status}. Dati copiati negli appunti per Discord.",
        "en": "{name} added to {status}. Data copied to clipboard for Discord.",
    },
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
        "it": "Distribuzione per nazione (membri attuali, top 15)",
        "en": "Distribution by nation (current members, top 15)",
    },
    "stats.nation_chart_hint": {
        "it": "Passa il mouse su una barra per vedere i nomi, tasto destro per altre opzioni.",
        "en": "Hover a bar to see the names, right-click for more options.",
    },
    "stats.nation_menu.copy": {"it": "Copia elenco nomi", "en": "Copy list of names"},
    "stats.nation_menu.open": {"it": "Apri in Membri attuali: {nation}", "en": "Open in Current members: {nation}"},
    "stats.top_rejoiners": {"it": "Membri con più rientri", "en": "Members with the most rejoins"},
    "stats.top_rejoiners_line": {"it": "{name} ({main}) — {count} rientri", "en": "{name} ({main}) — {count} rejoins"},
    "stats.ban_reasons": {"it": "Motivi di ban più comuni", "en": "Most common ban reasons"},
    "stats.ban_reasons_line": {"it": "{reason} — {count} casi", "en": "{reason} — {count} cases"},
    "stats.hall_of_fame": {"it": "Hall of fame (membri attuali più anziani)", "en": "Hall of fame (longest-standing current members)"},
    "stats.hall_of_fame_line": {"it": "{name} ({main}) — dal {since}", "en": "{name} ({main}) — since {since}"},
    "stats.no_data": {"it": "Nessun dato disponibile.", "en": "No data available."},

    # -- Calendario -----------------------------------------------------------
    "color.red": {"it": "Rosso", "en": "Red"},
    "color.orange": {"it": "Arancione", "en": "Orange"},
    "color.yellow": {"it": "Giallo", "en": "Yellow"},
    "color.lime": {"it": "Verde lime", "en": "Lime"},
    "color.green": {"it": "Verde", "en": "Green"},
    "color.teal": {"it": "Verde acqua", "en": "Teal"},
    "color.cyan": {"it": "Azzurro", "en": "Light blue"},
    "color.blue": {"it": "Blu", "en": "Blue"},
    "color.indigo": {"it": "Indaco", "en": "Indigo"},
    "color.purple": {"it": "Viola", "en": "Purple"},
    "color.magenta": {"it": "Magenta", "en": "Magenta"},
    "color.pink": {"it": "Rosa", "en": "Pink"},
    "color.brown": {"it": "Marrone", "en": "Brown"},
    "color.gray": {"it": "Grigio", "en": "Gray"},
    "color.black": {"it": "Nero", "en": "Black"},
    "calendar.today": {"it": "Oggi", "en": "Today"},
    "calendar.add": {"it": "Aggiungi evento", "en": "Add event"},
    "calendar.no_events": {"it": "Nessun evento in questo giorno.", "en": "No events on this day."},
    "calendar.more_events": {"it": "+{n} altri", "en": "+{n} more"},
    "calendar.dialog.new": {"it": "Nuovo evento", "en": "New event"},
    "calendar.dialog.edit": {"it": "Modifica evento", "en": "Edit event"},
    "calendar.field.title": {"it": "Titolo", "en": "Title"},
    "calendar.field.date": {"it": "Data", "en": "Date"},
    "calendar.field.color": {"it": "Colore", "en": "Color"},
    "calendar.field.note": {"it": "Nota (opzionale)", "en": "Note (optional)"},
    "calendar.field.repeat": {"it": "Ripetizione", "en": "Repeat"},
    "calendar.field.every": {"it": "Ogni", "en": "Every"},
    "calendar.field.end_check": {"it": "Ripeti fino al", "en": "Repeat until"},
    "calendar.repeat.none": {"it": "Non si ripete", "en": "Does not repeat"},
    "calendar.repeat.daily": {"it": "Ogni giorno", "en": "Daily"},
    "calendar.repeat.weekly": {"it": "Ogni settimana", "en": "Weekly"},
    "calendar.repeat.monthly": {"it": "Ogni mese", "en": "Monthly"},
    "calendar.unit.days": {"it": "giorni", "en": "days"},
    "calendar.unit.weeks": {"it": "settimane", "en": "weeks"},
    "calendar.unit.months": {"it": "mesi", "en": "months"},
    "calendar.recurring_hint": {"it": "Si ripete ogni {n} {unit}", "en": "Repeats every {n} {unit}"},
    "calendar.error.title_required": {"it": "Il titolo è obbligatorio.", "en": "The title is required."},
    "calendar.error.end_before_start": {
        "it": "La data di fine ripetizione non può precedere quella dell'evento.",
        "en": "The repeat end date can't be before the event date.",
    },
    "calendar.delete.title": {"it": "Elimina evento", "en": "Delete event"},
    "calendar.delete.body": {"it": "Eliminare l'evento \"{title}\"?", "en": "Delete the event \"{title}\"?"},
    "calendar.delete.body_series": {
        "it": "Eliminare l'evento \"{title}\"? È ricorrente: verranno eliminate tutte le sue ripetizioni.",
        "en": "Delete the event \"{title}\"? It's recurring: all its repetitions will be deleted.",
    },

    # -- Stato server BDO (footer, scheda BDO, impostazioni) -----------------
    "nav.bdo": {"it": "BDO", "en": "BDO"},
    "bdo.title": {"it": "Black Desert", "en": "Black Desert"},
    "bdo.server_status": {"it": "Stato dei server", "en": "Server status"},
    "bdo.refresh": {"it": "Aggiorna ora", "en": "Refresh now"},
    "footer.server_status": {"it": "Stato server", "en": "Server status"},
    "server.online": {"it": "Online", "en": "Online"},
    "server.maintenance": {"it": "In manutenzione", "en": "Under maintenance"},
    "server.maintenance_remaining": {"it": "In manutenzione (fine tra {time})", "en": "Under maintenance ({time} left)"},
    "server.unknown": {"it": "n/d", "en": "n/a"},
    "server.error.no_key": {
        "it": "Chiave API non configurata (Impostazioni → Server BDO)",
        "en": "API key not set (Settings → BDO servers)",
    },
    "server.error.auth": {"it": "Chiave API non valida", "en": "Invalid API key"},
    "server.error.rate_limit": {"it": "Troppe richieste, riprovo più tardi", "en": "Too many requests, will retry later"},
    "server.error.network": {"it": "Servizio non raggiungibile", "en": "Service unreachable"},
    "server.error.bad_response": {"it": "Risposta non valida dal servizio", "en": "Invalid response from the service"},
    "region.eu": {"it": "Europa (PC)", "en": "Europe (PC)"},
    "region.na": {"it": "Nord America (PC)", "en": "North America (PC)"},
    "region.console-eu": {"it": "Europa (Console)", "en": "Europe (Console)"},
    "region.console-na": {"it": "Nord America (Console)", "en": "North America (Console)"},
    "region.kr": {"it": "Corea (PC)", "en": "Korea (PC)"},
    "region.sa": {"it": "Sud America (PC)", "en": "South America (PC)"},
    "region.asia": {"it": "Asia (PC)", "en": "Asia (PC)"},
    "settings.bdo_title": {"it": "Server BDO (bdoalerts.net)", "en": "BDO servers (bdoalerts.net)"},
    "settings.bdo_hint": {
        "it": "Chiave API personale di bdoalerts.net, usata per mostrare lo stato dei server. "
        "Resta solo su questo computer, nel database locale.",
        "en": "Your personal bdoalerts.net API key, used to show the server status. "
        "It stays only on this computer, in the local database.",
    },
    "settings.bdo_key_placeholder": {"it": "Chiave API", "en": "API key"},
    "settings.bdo_region_label": {"it": "Regione mostrata nel footer", "en": "Region shown in the footer"},

    # -- Note --------------------------------------------------------------
    "notes.placeholder": {
        "it": "Scrivi qui le note della gilda... vengono salvate automaticamente.",
        "en": "Write the guild's notes here... they're saved automatically.",
    },
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
