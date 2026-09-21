# Night_Shade Manager

App desktop per gestire l'elenco membri della gilda Night_Shade (Black Desert Online): Attuali, Ex membri, Bannati, con storico dei movimenti tra liste, note, calendario eventi e statistiche.

## Avvio in sviluppo

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python -m gilda_app.main
```

Al primo avvio, se il database `gilda.db` è vuoto e nella cartella è presente `List 2026.xlsx`, l'app propone l'import iniziale.

## Test

```bash
venv\Scripts\python -m pytest tests/ -v
```

## Build dell'eseguibile Windows

```bash
venv\Scripts\pyinstaller gilda_app.spec
```

Il risultato è in `dist/Night_Shade Manager/` — una cartella (non un unico `.exe`) che contiene `Night_Shade Manager.exe` più le dipendenze. Il database `gilda.db` e la cartella `backups/` vengono creati accanto all'eseguibile: per backup o trasferimento su un altro PC basta copiare l'intera cartella `dist/Night_Shade Manager/`.

Per aggiornare l'app senza perdere i dati: sostituire solo `Night_Shade Manager.exe` e la cartella `_internal/`, lasciando `gilda.db` e `backups/` dove sono. Lo schema del database si aggiorna da solo all'avvio.

## Struttura del progetto

- `gilda_app/db/` — schema SQLite versionato, connessione, backup, statistiche, eventi del calendario
- `gilda_app/importer/` — import/export da e verso Excel (.xlsx)
- `gilda_app/ui/` — finestra principale e dialog (PySide6 + PySide6-Fluent-Widgets)
- `gilda_app/resources/flags/` — PNG delle bandiere (una per codice ISO alpha-2), generate una tantum con `scripts/extract_flags.py` e committate nel repo; non serve rigenerarle a meno di voler aggiungere una nazione mancante
- `tests/` — test automatici su import, CRUD, statistiche, calendario e formato date

Le date sono salvate nel database come `yyyy-mm-dd` (si ordinano correttamente come testo) e mostrate all'utente come `dd-mm-yyyy`.
