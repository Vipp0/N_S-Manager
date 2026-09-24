"""Cronologia delle versioni rilasciate, mostrata in Impostazioni -> Changelog.

Unica fonte da aggiornare ad ogni release (in cima, più recente per prima), insieme al
numero in version.py. Le note sono per l'utente finale: descrivono cosa cambia per chi
usa il programma, non i dettagli tecnici del come."""

CHANGELOG: list[dict] = [
    {
        "version": "2.0.11",
        "date": "24-09-2026",
        "notes": [
            "Modifica membro: nuovo pulsante \"Profilo BDO...\" con gilda e ruolo (Guild Master o membro), personaggio principale con classe e livello, numero di personaggi, gear score, punti contributo, energia e data di creazione della famiglia. Richiede la chiave API.",
            "Scheda BDO: nuovo confronto con la gilda in gioco (nome della gilda in Impostazioni): chi è in gioco ma non nel programma, chi è registrato come ex membro o bannato ma risulta ancora in gilda, e chi è tra i Membri attuali ma non si trova in gioco. Solo consultazione, nessuna modifica automatica.",
        ],
    },
    {
        "version": "2.0.10",
        "date": "24-09-2026",
        "notes": [
            "Scheda BDO: nuovi blocchi con i reset (giornaliero, settimanale, consegna imperiale, commercio, baratto, Black Shrine), il ciclo giorno/notte e i prossimi boss, con conti alla rovescia sempre aggiornati e orari nel fuso del computer.",
            "Dashboard: linea di separazione netta tra i riquadri delle schede e le informazioni generali, e nuova card con i timer BDO (prossimo boss, reset giornaliero, consegna imperiale).",
        ],
    },
    {
        "version": "2.0.9",
        "date": "24-09-2026",
        "notes": [
            "Dashboard: logo nell'intestazione e una seconda fascia con gli ultimi ingressi, i prossimi anniversari in gilda e la top 5 delle nazioni.",
            "Statistiche: nuova sezione con i prossimi anniversari di ingresso in gilda (60 giorni).",
        ],
    },
    {
        "version": "2.0.8",
        "date": "24-09-2026",
        "notes": [
            "Storico movimenti e storico nomi: le righe sono numerate (1, 2, 3...) e quelle dello storico nomi alternano due tonalità, per seguirle meglio scorrendo.",
            "Tolta la frase di spiegazione sotto lo storico nomi, che occupava spazio.",
        ],
    },
    {
        "version": "2.0.7",
        "date": "24-09-2026",
        "notes": [
            "Modifica membro: storico movimenti e storico nomi sono in due riquadri separati con bordo e titolo, più facili da distinguere.",
        ],
    },
    {
        "version": "2.0.6",
        "date": "24-09-2026",
        "notes": [
            "Nuovo Storico nomi nella modifica membro: i cambi di Family Name vengono registrati da soli (vecchio nome, nuovo nome, data) e si possono anche aggiungere, correggere o eliminare a mano.",
            "La ricerca (per lista e globale) trova un membro anche cercando un nome che non usa più.",
        ],
    },
    {
        "version": "2.0.5",
        "date": "24-09-2026",
        "notes": [
            "Dashboard: il riquadro sotto il mouse si tinge di azzurro tenue con un sottile bordo, per capire subito quale si sta per aprire.",
        ],
    },
    {
        "version": "2.0.4",
        "date": "24-09-2026",
        "notes": [
            "Storico movimenti nella modifica membro: le righe hanno sempre la stessa altezza, prima all'apertura risultavano più alte che dopo il salvataggio.",
        ],
    },
    {
        "version": "2.0.3",
        "date": "24-09-2026",
        "notes": [
            "Modifica membro: su finestre larghe i dati e lo storico movimenti stanno affiancati in due colonne, invece di una lunga colonna da scorrere.",
        ],
    },
    {
        "version": "2.0.2",
        "date": "24-09-2026",
        "notes": [
            "Storico movimenti di un membro con righe colorate: verde il primo ingresso, giallo il passaggio a ex membro, rosso il ban, azzurro il rientro.",
        ],
    },
    {
        "version": "2.0.1",
        "date": "24-09-2026",
        "notes": [
            "Il controllo aggiornamenti riconosce le versioni scritte senza il terzo numero (es. 2.1).",
        ],
    },
    {
        "version": "2.0.0",
        "date": "24-09-2026",
        "notes": [
            "Nuova Dashboard, ora scheda iniziale: un riquadro per ogni scheda (liste membri, statistiche, calendario, BDO, note, impostazioni) con un riassunto, e un click apre la scheda corrispondente.",
            "Azioni rapide in cima alla dashboard: aggiungi membro, nuovo evento, backup ora.",
            "Nei riquadri: ingressi/uscite/ban degli ultimi 30 giorni, ultimi movimenti, prossimi eventi e festività, stato del server BDO con manutenzione annunciata, anteprima delle note, ultimo backup.",
        ],
    },
    {
        "version": "1.11.0",
        "date": "24-09-2026",
        "notes": [
            "Scheda BDO: nuovo blocco con gli ultimi avvisi ufficiali (NA/EU), cliccabili, con le manutenzioni in evidenza.",
            "Se c'è una manutenzione già annunciata, la scheda ne mostra la data (l'orario preciso resta nella pagina dell'avviso).",
        ],
    },
    {
        "version": "1.10.1",
        "date": "24-09-2026",
        "notes": [
            "Nuovo pulsante \"Rimuovi chiave\" in Impostazioni: cancella la chiave API dal database (anche fisicamente dal file), utile prima di condividere il database.",
        ],
    },
    {
        "version": "1.10.0",
        "date": "24-09-2026",
        "notes": [
            "Stato dei server di Black Desert: in fondo alla finestra, a destra, compare online/in manutenzione della regione scelta (con il tempo rimasto), aggiornato ogni 5 minuti.",
            "Nuova scheda BDO con lo stato di tutte le regioni; ci si arriva anche cliccando sul footer.",
            "In Impostazioni si inserisce la propria chiave API di bdoalerts.net (salvata solo sul computer) e si sceglie la regione mostrata nel footer.",
        ],
    },
    {
        "version": "1.9.0",
        "date": "23-09-2026",
        "notes": [
            "Nuovo pulsante \"Ricostruisci storico...\" nella scheda di modifica membro: permette di inserire in un colpo solo tutti i passaggi già avvenuti (entrato, uscito, rientrato...) con le rispettive date, utile per ricostruire lo storico di chi era già nel database prima che venisse tracciato.",
            "Le date si possono ora anche scrivere a mano (formato gg-mm-aaaa) invece di scegliere solo dal calendarietto.",
        ],
    },
    {
        "version": "1.8.5",
        "date": "23-09-2026",
        "notes": [
            "Logo dell'intestazione ingrandito, era troppo piccolo su schermi larghi.",
        ],
    },
    {
        "version": "1.8.4",
        "date": "23-09-2026",
        "notes": [
            "Nuovo logo nell'intestazione delle liste: \"Night_Shade\" e \"Manager\" nello stesso stile decorato, invece di due font diversi uniti a mano.",
        ],
    },
    {
        "version": "1.8.3",
        "date": "23-09-2026",
        "notes": [
            "Testo \"Loading...\" della schermata di caricamento ora davvero centrato.",
        ],
    },
    {
        "version": "1.8.2",
        "date": "23-09-2026",
        "notes": [
            "Testo \"Loading...\" della schermata di caricamento spostato più in basso, con più spazio attorno.",
        ],
    },
    {
        "version": "1.8.1",
        "date": "23-09-2026",
        "notes": [
            "Nuova immagine per la schermata di caricamento, con il testo \"Loading...\" animato.",
        ],
    },
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
