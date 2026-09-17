# Gestionale Membri Gilda

App desktop per gestire l'elenco membri della gilda (Black Desert Online): Attuali, Ex membri, Bannati, con storico dei movimenti tra liste.

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

Il risultato è in `dist/GestionaleGilda/` — una cartella (non un unico `.exe`) che contiene `GestionaleGilda.exe` più le dipendenze. Il database `gilda.db` e la cartella `backups/` vengono creati accanto all'eseguibile: per backup o trasferimento su un altro PC basta copiare l'intera cartella `dist/GestionaleGilda/`.

## Struttura del progetto

- `gilda_app/db/` — schema SQLite versionato, connessione, backup, statistiche
- `gilda_app/importer/` — import/export da e verso Excel (.xlsx)
- `gilda_app/ui/` — finestra principale e dialog (PySide6 + PySide6-Fluent-Widgets)
- `gilda_app/resources/flags/` — PNG delle bandiere (una per codice ISO alpha-2), generate una tantum con `scripts/extract_flags.py` e committate nel repo; non serve rigenerarle a meno di voler aggiungere una nazione mancante
- `tests/` — test automatici su import, CRUD e statistiche
