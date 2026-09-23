"""Cronologia delle versioni rilasciate, mostrata in Impostazioni -> Changelog.

Unica fonte da aggiornare ad ogni release (in cima, più recente per prima), insieme al
numero in version.py. Le note sono per l'utente finale: descrivono cosa cambia per chi
usa il programma, non i dettagli tecnici del come."""

CHANGELOG: list[dict] = [
    {
        "version": "1.8.0",
        "date": "23-09-2026",
        "notes": [
            "All'avvio il programma controlla se è disponibile una versione più recente e, se sì, propone di aprire la pagina per scaricarla (mai in automatico).",
        ],
    },
    {
        "version": "1.7.1",
        "date": "23-09-2026",
        "notes": [
            "Colori disponibili per gli eventi del calendario: da 11 a 15 (aggiunti verde lime, verde acqua, indaco, magenta).",
        ],
    },
    {
        "version": "1.7.0",
        "date": "23-09-2026",
        "notes": [
            "Nuovo pulsante \"Storico modifiche (changelog)\" in Impostazioni: mostra l'elenco di tutte le versioni rilasciate e cosa è cambiato in ognuna.",
        ],
    },
    {
        "version": "1.6.0",
        "date": "23-09-2026",
        "notes": [
            "Le festività della Corea del Sud compaiono nel calendario, aggiornate da internet in sottofondo (senza rallentare l'avvio).",
        ],
    },
    {
        "version": "1.5.2",
        "date": "23-09-2026",
        "notes": [
            "Il pallino colorato degli eventi nel calendario è ora perfettamente tondo e centrato rispetto al testo.",
        ],
    },
    {
        "version": "1.5.1",
        "date": "23-09-2026",
        "notes": [
            "Testo degli eventi nel calendario più grande.",
            "Tolta la barra di selezione nativa di Windows che compariva accanto al giorno selezionato.",
        ],
    },
    {
        "version": "1.5.0",
        "date": "23-09-2026",
        "notes": [
            "Nel calendario si vede subito il titolo di ogni evento nella cella del giorno, con un pallino del colore dell'evento davanti.",
        ],
    },
    {
        "version": "1.4.0",
        "date": "23-09-2026",
        "notes": [
            "Nel calendario, la settimana e il giorno corrente sono evidenziati con un bordo colorato.",
            "Nuovo pulsante \"Oggi\" per tornare subito alla settimana corrente.",
        ],
    },
    {
        "version": "1.3.0",
        "date": "21-09-2026",
        "notes": [
            "Backup automatico giornaliero all'avvio (tiene le ultime 30 copie).",
            "Backup manuale su richiesta e ripristino da un backup precedente, da Impostazioni.",
            "Possibilità di salvare una seconda copia dei backup su un altro disco.",
        ],
    },
    {
        "version": "1.2.4",
        "date": "21-09-2026",
        "notes": [
            "Il riavvio dopo il cambio lingua non lascia più visibile per qualche secondo la finestra vecchia.",
        ],
    },
    {
        "version": "1.2.3",
        "date": "21-09-2026",
        "notes": [
            "Il form di aggiunta/modifica membro ora scorre invece di uscire dai bordi quando la finestra è piccola.",
        ],
    },
    {
        "version": "1.2.2",
        "date": "21-09-2026",
        "notes": [
            "Scritta \"Night_Shade\" del logo scontornata correttamente, senza lettere tagliate.",
        ],
    },
    {
        "version": "1.2.1",
        "date": "21-09-2026",
        "notes": [
            "La finestra si apre subito in primo piano invece di restare nascosta dietro le altre.",
        ],
    },
    {
        "version": "1.2.0",
        "date": "21-09-2026",
        "notes": [
            "Schermata di caricamento mostrata subito all'avvio, mentre il programma si prepara.",
        ],
    },
    {
        "version": "1.1.0",
        "date": "21-09-2026",
        "notes": [
            "Nel form di nuovo membro si può scegliere subito in quale lista inserirlo.",
        ],
    },
    {
        "version": "1.0.1",
        "date": "21-09-2026",
        "notes": [
            "La X per cancellare la ricerca resta visibile finché c'è testo nel campo.",
        ],
    },
    {
        "version": "1.0.0",
        "date": "21-09-2026",
        "notes": [
            "Numero di versione mostrato nel titolo della finestra e in Impostazioni.",
        ],
    },
]
