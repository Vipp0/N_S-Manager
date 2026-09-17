# Piano per Claude Code – Gestionale Membri Gilda

2026-09-16 · @Someone

## Obiettivo

Creare un programma desktop per gestire l'elenco membri della gilda su **Black Desert Online**, usato dal fratello di Fabrizio. Sostituisce l'attuale gestione via file Excel con un'app che tiene traccia di tre liste — **Membri attuali**, **Ex membri** (possono rientrare) e **Bannati** (non possono rientrare) — permettendo di consultarle, modificarle e spostare i membri tra liste in modo semplice e veloce, con tasto destro per copiare i dati.

## Stack tecnico

- **Linguaggio/UI:** Python + PySide6 (Qt) — già usato con successo in Spot Cutter Ultra; per un'app centrata su tabelle (ordinamento, selezione, menu contestuale sulle righe) offre widget nativi più completi rispetto a CustomTkinter
- **Storage:** SQLite locale (file `.db` unico), tramite il modulo `sqlite3` della standard library — nessuna dipendenza esterna da installare
- **Excel:** `openpyxl` per import/export `.xlsx`
- **Distribuzione:** eseguibile Windows standalone via PyInstaller, così il fratello lo lancia senza installare Python
- **Perché non un file Excel live:** editare direttamente un `.xlsx` ad ogni azione (spostamento, aggiunta) è lento, rischia corruzione del file e rende difficile mantenere uno storico dei movimenti tra liste
- **Backup automatico:** salvataggio di una copia del database prima di ogni import in blocco e prima di ogni spostamento tra liste, per poter tornare indietro in caso di errore

## Modello dati

Dal file Excel originale si useranno solo le prime 5 colonne (il resto ignorato, come confermato):

| Campo | Descrizione |
| --- | --- |
| Family Name | Nome principale/cognome del personaggio |
| Main Name | Nome secondario/alt |
| Nation | Nazionalità (può essere più di una — doppia nazionalità gestita come lista di 1 o 2 valori) |
| Discord Name | Nome su Discord |

Ogni membro ha inoltre, gestiti internamente dal programma:

| Campo interno | Descrizione |
| --- | --- |
| id | identificativo univoco |
| status | `attivo` \| `ex_membro` \| `bannato` |
| data\_inserimento | quando è entrato nella lista attuale |
| note | campo libero opzionale |

**Storico movimenti:** tabella separata con id membro, stato precedente, stato nuovo, data del movimento e nota opzionale (es. motivo del ban). Permette di rispondere a "quando è stato bannato X" o "quante volte è rientrato Y", e alimenta le statistiche.

Questo sostituisce le tre liste separate del file Excel: un unico elenco membri con uno `status`, più lo storico dei cambi di stato.

**Possibili estensioni future** (non nella prima versione, da valutare in un secondo momento): ruolo in gilda (master/officer/membro), livello personaggio, classe, ultima attività, lingua principale, fonte di reclutamento. Il modello dati va pensato in modo da poter aggiungere colonne senza dover rifare l'import o la struttura esistente.

Per gestirlo bene fin da subito conviene prevedere uno **schema versionato** (una tabella `schema_version` + script di migrazione incrementali): così in futuro si aggiungono colonne ai dati già esistenti senza dover ricreare il database da zero.

## Import ed export Excel

**Import iniziale** (una tantum, per popolare il database dal file attuale):

- Foglio "Members" → status `attivo` (ha intestazioni, prime 5 colonne)
- Foglio "Old Members" → status `ex_membro` (senza intestazioni: prima riga già dato, stesse colonne base; righe vuote nel mezzo da saltare)
- Foglio "No Rejoin" → status `bannato` (senza intestazioni; struttura colonne da confermare — probabile che 3 delle 4 colonne siano nomi alternativi/nickname dello stesso utente e la quarta la nazionalità, da verificare con il fratello prima dell'import)
- Anteprima prima di confermare l'import, con conteggio righe importate/scartate per foglio
- Alcuni valori di Nation contengono già più nazionalità separate da "/" (es. "Algeria/Dubai", "Turkey/Germany") — lo script di import deve riconoscere lo slash e splittarle in due nazionalità separate
- Per i membri già presenti in Old Members / No Rejoin la data di ingresso non è nota: il campo `data_inserimento` resta vuoto per questi record (si compila normalmente per i nuovi inserimenti futuri)

**Import ricorrente:** stessa funzione riutilizzabile in futuro per aggiungere in blocco nuovi nominativi da un file Excel, con controllo duplicati (su Family Name + Main Name): se un nominativo importato corrisponde già a un membro presente in una lista, il programma mostra un avviso ("Questo utente è già presente nella lista ... — vuoi aggiungerlo comunque o è lo stesso utente?") e lascia scegliere se saltarlo, aggiornarlo o inserirlo comunque come nuova voce

**Export:** genera un `.xlsx` con lo stesso formato a 3 fogli, così il fratello può comunque avere un backup/copia leggibile fuori dal programma quando vuole

## Funzionalità interfaccia

- **Tab per lista:** Attuali / Ex membri / Bannati, ognuna con tabella ordinata alfabeticamente (per Family Name di default, colonne cliccabili per riordinare) — all'avvio si apre sempre la lista **Attuali**
- **Ricerca/filtro** in tempo reale sopra la tabella
- **Bandierina/e del paese** accanto al nome della nazione in tabella — se il membro ha doppia nazionalità, mostra entrambe le bandierine affiancate
- **Tasto destro su una riga:** copia riga intera, copia singolo campo (es. solo Discord Name), modifica, sposta in un'altra lista, elimina
- **Sposta membro:** dalla lista Attuali → Ex membri o Bannati; da Ex membri → Attuali (rientro) o Bannati; da Bannati nessun rientro previsto salvo intervento manuale — ogni spostamento chiede conferma e registra data + eventuale nota nello storico
- **Inserimento manuale:** form con i campi base, validazione minima (Family Name obbligatorio)
- **Modifica membro esistente** tramite doppio click o dal menu tasto destro

**Stile grafico:** interfaccia moderna e accattivante, non il classico aspetto "widget di sistema anni '80" tipico di Qt/PySide6 di default — per ottenerlo si può usare una libreria di stile sopra PySide6 (es. **PySide6-Fluent-Widgets** o **qt-material**) che dà gratis un look flat/moderno con palette colori, icone e componenti già curati, oppure un QSS (stylesheet Qt) personalizzato scritto ad hoc. Priorità comunque alla semplicità d'uso per un utente non tecnico.

## Statistiche

- Conteggio membri per lista (Attuali / Ex / Bannati) e totale storico
- Distribuzione per nazione (utile per capire la composizione della gilda)
- Movimenti nel tempo: ingressi, uscite, ban, rientri per periodo (grafico o tabella per mese/anno)
- Membri con più "rientri" (utile per capire chi va e viene spesso)
- Andamento nel tempo del numero di membri attivi (grafico a linea, crescita/calo netto mese per mese)
- Tempo medio di permanenza prima di uscire o essere bannato
- Tasso di rientro: percentuale di ex membri effettivamente tornati sul totale degli ex membri
- Membri aggiunti/usciti negli ultimi 30-90 giorni (vista "recente")
- Motivi di ban più comuni, se registrati nella nota dello storico movimenti
- Longevità: membri attuali ordinati per anzianità ("hall of fame")

## Fasi di sviluppo consigliate per Claude Code

1. **Schema database + import Excel una tantum** — creare il `.db`, scrivere lo script di import dal `List_2026.xlsx` esistente, verificare i conteggi (114 attuali, \~536 ex membri al netto delle righe vuote, 23 bannati)
2. **Vista lista base** — tab con le tre liste, tabella ordinata alfabeticamente, ricerca
3. **Tasto destro + copia** — menu contestuale con copia riga/campo
4. **CRUD membri** — inserimento manuale, modifica, eliminazione
5. **Spostamento tra liste** — con conferma e registrazione nello storico movimenti
6. **Export Excel** — generazione del file a 3 fogli
7. **Statistiche** — dashboard riepilogativa
8. **Packaging** — build dell'eseguibile Windows con PyInstaller

Ogni fase è testabile singolarmente prima di passare alla successiva, così il fratello può iniziare a usare le funzioni base (consultazione + copia) anche prima che il programma sia completo.
