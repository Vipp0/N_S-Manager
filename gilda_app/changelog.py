"""Cronologia delle versioni rilasciate, mostrata in Impostazioni -> Changelog.

Unica fonte da aggiornare ad ogni release (in cima, più recente per prima), insieme al
numero in version.py. Le note sono per l'utente finale: descrivono cosa cambia per chi
usa il programma, non i dettagli tecnici del come."""

CHANGELOG: list[dict] = [
    {
        "version": "2.1.7",
        "date": "25-09-2026",
        "notes": [
            "Dashboard: le righe di oggi sono ora in verde scuro invece che in arancio.",
        ],
    },
    {
        "version": "2.1.6",
        "date": "25-09-2026",
        "notes": [
            "Dashboard: in tutti i riquadri i giorni vicini sono scritti \"Oggi\", \"Domani\" e \"Ieri\" invece della data (calendario, compleanni, anniversari, ultimi ingressi, ultimi movimenti).",
            "Compleanno: cliccando sul giorno si può scrivere subito, senza cancellare il trattino; il mese si completa mentre si scrive (\"se\" diventa \"settembre\").",
        ],
    },
    {
        "version": "2.1.5",
        "date": "25-09-2026",
        "notes": [
            "Dashboard: le righe che riguardano oggi (eventi, festività, compleanni, anniversari) sono in grassetto e colorate.",
            "Ricostruisci storico: si può indicare \"Sconosciuta\" come data di un passaggio, si possono mettere due passaggi consecutivi nella stessa lista (con un avviso, ma senza blocco) e i passaggi si spostano su e giù; nuovo pulsante \"Ordina per data\". L'ordine dello storico segue ora la sequenza dei passaggi.",
            "Correzione di una voce dello storico: possibile impostare la data come sconosciuta.",
            "Compleanno: frecce su/giù di nuovo affiancate a destra (quella che scende a sinistra di quella che sale); il giorno cicla passando dal vuoto e un pulsante azzera tutto il campo.",
            "Modifica membro: titoli delle sezioni più in alto e più spazio agli elenchi dello storico movimenti e dello storico nomi.",
        ],
    },
    {
        "version": "2.1.4",
        "date": "24-09-2026",
        "notes": [
            "Campo Compleanno: il numero del giorno tornava invisibile con le frecce ai lati, ora si legge.",
        ],
    },
    {
        "version": "2.1.3",
        "date": "24-09-2026",
        "notes": [
            "Campo Compleanno: freccia sinistra per scendere e destra per salire, il giorno riparte da 1 dopo il 31 (e da 31 dopo l'1); il mese si può scegliere dal menù oppure scrivere a mano, con completamento; il segnaposto dell'anno ha più spazio.",
        ],
    },
    {
        "version": "2.1.2",
        "date": "24-09-2026",
        "notes": [
            "Campo Compleanno: il giorno ha più spazio e i numeri a due cifre si leggono per intero.",
        ],
    },
    {
        "version": "2.1.1",
        "date": "24-09-2026",
        "notes": [
            "Nuovo campo Compleanno nella scheda del membro (giorno e mese, anno facoltativo).",
            "Dashboard: nuova card Compleanni con quelli di oggi e dei prossimi 14 giorni (con l'età che compiono, se l'anno è noto).",
        ],
    },
    {
        "version": "2.1",
        "date": "24-09-2026",
        "notes": [
            "Modifica membro: nuovo Storico nomi (i cambi di Family Name si registrano da soli, e si possono aggiungere, correggere o eliminare a mano). La ricerca trova un membro anche con un nome che non usa più.",
            "Modifica membro: dati e storico affiancati in due colonne su finestre larghe; storico movimenti e storico nomi in riquadri separati, con righe numerate e colorate (verde ingresso, giallo ex membro, rosso ban, azzurro rientro).",
            "Modifica membro: pulsante \"Profilo BDO...\" con gilda e ruolo, personaggio principale, gear score, punti contributo ed energia.",
            "Dashboard: ora scheda iniziale, con logo, riquadri cliccabili per ogni scheda (evidenziati al passaggio del mouse) e azioni rapide; sotto, informazioni generali con ultimi ingressi, anniversari in gilda, top 5 nazioni e timer BDO.",
            "Statistiche: nuova sezione con i prossimi anniversari di ingresso in gilda.",
            "Scheda BDO: reset (giornaliero, settimanale, consegna imperiale...), ciclo giorno/notte e prossimi boss con conti alla rovescia, e confronto con la gilda in gioco (chi manca nel programma, chi risulta ex o bannato ma è ancora in gilda, chi non si trova in gioco).",
            "Piccole correzioni: righe dello storico sempre della stessa altezza; il controllo aggiornamenti riconosce le versioni scritte senza il terzo numero.",
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
