"""Cronologia delle versioni rilasciate, mostrata in Impostazioni -> Changelog.

Unica fonte da aggiornare ad ogni release (in cima, più recente per prima), insieme al
numero in version.py. Le note sono per l'utente finale: descrivono cosa cambia per chi
usa il programma, non i dettagli tecnici del come."""

CHANGELOG: list[dict] = [
    {
        "version": "2.5",
        "date": "05-10-2026",
        "notes": [
            "Avviso doppioni: aggiungendo un membro (o cambiando il Family Name di uno esistente), se quel nome c'è già in una qualunque lista (attuali, ex membri, bannati) compare un avviso con le persone trovate. Da lì si può aprire direttamente la scheda del membro già presente, andare avanti comunque o tornare al modulo. Anche il controllo dei doppioni dell'import da Excel non distingue più tra maiuscole e minuscole.",
            "Dashboard → Compleanni: ora compaiono anche quelli degli ex membri, con \"(ex membro)\" accanto al nome; il giorno del compleanno la riga diventa ambra (verde per i membri attuali). I bannati restano esclusi. Il riquadro mostra fino a 8 compleanni invece di 6, con precedenza ai membri attuali a parità di data.",
            "Calendario: tasto destro su un evento nella colonna di destra per copiare la nota (\"Copia nota\"), copiare titolo e nota insieme, modificare, eliminare o duplicare l'evento. \"Duplica evento\" apre il form già compilato con titolo, nota, colore e ricorrenza dell'originale: di solito basta cambiare la data.",
            "Finestre di aggiunta/modifica membro e di evento del calendario: ora si possono spostare trascinandole dal titolo (o da un punto vuoto del riquadro), per leggere quello che c'è sotto. Non restano mai fuori dalla finestra e, alla riapertura, tornano sempre al centro.",
            "Una sola copia del programma alla volta: se lo si apre mentre è già aperto, la finestra già esistente torna in primo piano invece di aprirne una seconda sullo stesso database (che avrebbe mostrato dati non aggiornati).",
            "Registro degli errori: se il programma incontra un errore imprevisto (o si chiude all'improvviso) lo annota nel file \"errori.log\", accanto al programma, con data e versione. Se qualcosa non funziona basta mandare quel file per capire cos'è successo (un file vuoto significa nessun errore).",
            "Ricostruisci storico: prima di sostituire lo storico di un membro il programma fa ora una copia di sicurezza del database (recuperabile da Impostazioni → Ripristina), come già avviene per spostamenti, import e azzeramento. Se la copia non riesce, lo storico non viene toccato.",
            "Importa da Excel: un file creato con \"Esporta in Excel\" ora si può reimportare correttamente (prima la scheda Membri attuali scambiava le colonne e le intestazioni venivano scambiate per persone). Un errore di lettura del file ora viene sempre segnalato.",
            "Aggiornamento automatico: i dati dell'utente (database, copie di sicurezza, registro errori) non vengono mai sostituiti, nemmeno se finiscono per errore nel pacchetto di una release.",
            "Profilo BDO: se il giocatore ha nascosto la gilda dal proprio profilo compare \"Sconosciuta (profilo privato)\" invece di \"Nessuna gilda\"; quando il livello di un personaggio non è visibile non compare più un fuorviante \"livello 0\".",
            "Stato dei server e avvisi BDO: se la connessione cade a metà di una risposta, i controlli successivi ripartono regolarmente invece di fermarsi fino al riavvio. Festività: una risposta vuota o non valida dalla fonte online non cancella più le date già salvate.",
        ],
    },
    {
        "version": "2.4",
        "date": "30-09-2026",
        "notes": [
            "Calendario e dashboard: se il programma resta aperto per più giorni, \"oggi\" ora avanza da solo (il programma controlla ogni minuto), invece di restare fermo al giorno in cui era stato aperto.",
            "Dashboard: nuovo avviso rosso in cima quando c'è una manutenzione annunciata (\"Oggi\"/\"Domani\"/la data), cliccabile per aprire la scheda BDO. Quando inizia, il testo diventa \"In manutenzione\" (con il tempo restante) invece di sparire subito, e resta visibile finché il server non torna online da solo.",
            "Nuovo membro: anche nel form di aggiunta c'è ora il pulsante \"Profilo BDO...\", per vedere le caratteristiche di un giocatore (scrivendone il Family Name) prima ancora di deciderne l'ingresso in gilda, senza doverlo salvare prima.",
            "Impostazioni: aggiunti titolo e descrizione alla sezione \"Azzera database\", coerenti con le altre sezioni.",
            "Aggiornamento automatico: la schermata con la barra di avanzamento non passa più in secondo piano nel momento del passaggio tra il programma vecchio e quello nuovo.",
        ],
    },
    {
        "version": "2.3",
        "date": "28-09-2026",
        "notes": [
            "Profilo BDO: elenco completo dei personaggi (non più troncato a 12), raggruppati per classe e ordinati per livello, con i nomi; nuova sezione \"Vite da mestierante\" (raccolta, pesca, lavorazione...); la finestra ora scorre invece di crescere all'infinito. L'attesa per un profilo non ancora in memoria arriva fino a 30 secondi (prima si interrompeva dopo pochi secondi mostrando \"Servizio non raggiungibile\").",
            "Scheda BDO: la pagina ora scorre, non restano più tagliate le news in fondo quando sono tante; sotto i timer di reset/boss c'è scritto il nome vero della regione usata (es. \"Europa (PC)\"), non più \"quella scelta nel footer\".",
            "Footer \"Stato server\": senza chiave API il click apre direttamente Impostazioni (dove si inserisce la chiave) invece della scheda BDO.",
            "La finestra non si può più restringere al punto da nascondere il pulsante \"Impostazioni\" nel menù laterale.",
            "Impostazioni riorganizzate: pulsanti di dimensione normale invece che larghi quanto la finestra (affiancati dove ha senso, es. Importa/Esporta); \"Importa\"/\"Esporta\" hanno ora una sezione propria (\"Scambio dati con Excel\") spostata più in basso, sotto Backup.",
        ],
    },
    {
        "version": "2.2",
        "date": "25-09-2026",
        "notes": [
            "Aggiornamento automatico: quando c'è una nuova versione si può scegliere \"Installa ora\". Il programma fa una copia di sicurezza del database, scarica la versione, si aggiorna e si riavvia da solo, con una schermata con il logo e una barra di avanzamento. Se qualcosa non va, resta la versione precedente. In Impostazioni c'è il nuovo pulsante \"Controlla aggiornamenti\".",
            "Compleanni: nuovo campo nella scheda del membro (giorno e mese, anno facoltativo; il mese si scrive con completamento automatico) e nuova card in dashboard con i compleanni di oggi e dei prossimi 14 giorni, con l'età se l'anno è noto.",
            "Dashboard: le righe di oggi sono in grassetto verde scuro; in tutti i riquadri i giorni vicini sono scritti \"Oggi\", \"Domani\" e \"Ieri\" invece della data, con la prima parola di ogni riga in una colonna allineata.",
            "Ricostruisci storico: si può indicare \"Sconosciuta\" come data di un passaggio, si possono mettere due passaggi consecutivi nella stessa lista (con un avviso, ma senza blocco) e i passaggi si spostano su e giù; nuovo pulsante \"Ordina per data\". Anche la correzione di una voce dello storico permette la data sconosciuta.",
            "Modifica membro: titoli delle sezioni più in alto e più spazio agli elenchi dello storico movimenti e dello storico nomi.",
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
