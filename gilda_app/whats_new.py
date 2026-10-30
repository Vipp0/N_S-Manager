"""Novità mostrate in un popup al primo avvio dopo un aggiornamento.

Una voce per ogni release pubblicata, scritta per chi usa il programma: poche voci, ognuna con
un titolo breve e una frase chiara, senza termini tecnici, in italiano e in inglese (il
programma si usa in entrambe le lingue). Ci vanno le funzioni nuove e i difetti che l'utente
poteva davvero incontrare nella versione che aveva prima; un difetto nato e corretto tra due
release non si cita mai, perché nessuno l'ha visto. Il dettaglio completo resta in changelog.py."""
from dataclasses import dataclass

from gilda_app.utils.update_check import version_key

MAX_RELEASES_SHOWN = 3
# Lingua del popup. Per ora sempre italiano, anche se il programma è impostato in inglese: lo usa
# una sola persona, che sceglie l'inglese solo per coerenza con il gioco. Le traduzioni inglesi
# sono già scritte: per usarle basta mettere qui get_language() (da i18n) al posto di "it".
POPUP_LANGUAGE = "it"


@dataclass(frozen=True)
class Highlight:
    icon: str  # nome di un'icona di qfluentwidgets.FluentIcon (es. "CALENDAR")
    title: str
    text: str
    title_en: str = ""
    text_en: str = ""

    def localized(self, language: str) -> tuple[str, str]:
        """(titolo, testo) nella lingua richiesta; se manca la traduzione, in italiano."""
        if language == "en" and self.title_en and self.text_en:
            return self.title_en, self.text_en
        return self.title, self.text


# Chiave: versione della release (come in version.py, es. "2.6").
WHATS_NEW: dict[str, list[Highlight]] = {
    "2.9": [
        Highlight(
            "BOOK_SHELF",
            "Nuova scheda: Registro eventi",
            "Prima di Statistiche trovi lo storico di ciò che si fa nel programma, con data e ora: in verde chi entra "
            "o rientra tra i membri attuali, in rosso chi esce o viene bannato, senza colore cambi di nome, "
            "modifiche, eliminazioni e importazioni. Si può filtrare, cercare e, con un doppio click, andare al "
            "membro. Parte da ora, più gli ultimi 90 giorni già presenti nello storico.",
            "New tab: Event log",
            "Before Statistics you find the history of what is done in the program, with date and time: green for "
            "who joins or returns among the current members, red for who leaves or gets banned, no colour for name "
            "changes, edits, deletions and imports. You can filter, search and, with a double click, go to the "
            "member. It starts now, plus the last 90 days already in the history.",
        ),
        Highlight(
            "ADD",
            "Chi rientra compare tra gli ultimi ingressi",
            "In dashboard, negli Ultimi ingressi, ora ci sono anche i membri che tornano da ex membri o da bannati, "
            "con la data del rientro e la scritta \"rientrato\"; contano anche nel numero degli ingressi degli "
            "ultimi 30 giorni. Prima non venivano segnalati.",
            "Returning members show among the latest joins",
            "On the dashboard, in Latest joins, members coming back from ex members or banned now appear too, with the "
            "return date and the label \"rejoined\"; they also count in the number of joins of the last 30 days. "
            "Before, they were not shown.",
        ),
        Highlight(
            "BRUSH",
            "Tema di Natale",
            "Dall'8 dicembre al 6 gennaio il programma si veste a festa da solo, come a Halloween: nuova schermata di "
            "caricamento, logo e icona, pulsanti blu e decorazioni natalizie in ogni scheda. Puoi provarlo subito da "
            "Impostazioni → Tema stagionale.",
            "Christmas theme",
            "From 8 December to 6 January the program dresses up by itself, like at Halloween: new loading screen, "
            "logo and icon, blue buttons and Christmas decorations in every tab. You can try it right now from "
            "Settings → Seasonal theme.",
        ),
    ],
    "2.8": [
        Highlight(
            "BRUSH",
            "Temi per le feste",
            "Nei periodi di festa il programma cambia aspetto da solo: per ora c'è Halloween, fino al 2 novembre, con "
            "schermata di caricamento a tema, logo, icona, colore dei pulsanti e qualche decorazione negli angoli. "
            "Il 31 ottobre e il 1 novembre compare anche la scritta di auguri. Finita la festa torna tutto normale.",
            "Holiday themes",
            "During holidays the program changes its look by itself: for now there is Halloween, until 2 November, "
            "with a themed loading screen, logo, icon, button colour and a few decorations in the corners. On 31 "
            "October and 1 November a greeting also appears. When the holiday ends everything goes back to normal.",
        ),
        Highlight(
            "SETTING",
            "Tema stagionale in Impostazioni",
            "In Impostazioni → Tema stagionale puoi lasciare l'automatico, tenere sempre l'aspetto normale oppure "
            "provare Halloween fuori stagione.",
            "Seasonal theme in Settings",
            "In Settings → Seasonal theme you can keep it automatic, always use the normal look, or preview "
            "Halloween out of season.",
        ),
    ],
    "2.7.3": [
        Highlight(
            "INFO",
            "Fascia oraria e motivo della manutenzione",
            "Nella scheda BDO un blocco mostra la manutenzione con la fascia oraria in evidenza e, per le "
            "temporanee, il motivo scritto nell'avviso ufficiale (in inglese). Passando il mouse sul titolo si vede "
            "da dove viene l'orario.",
            "Maintenance time and reason",
            "In the BDO tab a block shows the maintenance with its time slot highlighted and, for temporary ones, "
            "the reason written in the official notice. Hovering the title shows where the time comes from.",
        ),
        Highlight(
            "DOCUMENT",
            "Ultime patch note",
            "Sempre nella scheda BDO compaiono le ultime tre patch note, con il link al sito: cosa cambia a ogni "
            "manutenzione.",
            "Latest patch notes",
            "The BDO tab also lists the latest three patch notes, with a link to the site: what changes with each "
            "maintenance.",
        ),
        Highlight(
            "UPDATE",
            "Nuove versioni anche a programma sempre aperto",
            "Se lasci il programma aperto per giorni, controlla da solo ogni 6 ore se c'è una nuova versione e te "
            "lo segnala con una striscia in alto, senza interrompere quello che stai facendo. A mezzanotte il "
            "calendario passa al nuovo giorno.",
            "New versions even if the program stays open",
            "If you leave the program open for days, it checks by itself every 6 hours for a new version and tells "
            "you with a bar at the top, without interrupting what you are doing. At midnight the calendar moves to "
            "the new day.",
        ),
    ],
    "2.7.2": [
        Highlight(
            "TILES",
            "Più manutenzioni, più banner",
            "Se ci sono più manutenzioni vicine, in cima alla dashboard compare un banner per ciascuna, uno sotto "
            "l'altro (fino a tre), ognuno con il suo colore e il suo orario.",
            "More maintenances, more banners",
            "When several maintenances are close together, the top of the dashboard shows one banner for each, "
            "stacked (up to three), each with its own colour and time.",
        ),
        Highlight(
            "TAG",
            "Manutenzione temporanea ben riconoscibile",
            "Durante una manutenzione temporanea il banner dice \"Manutenzione temporanea in corso\" e il riquadro "
            "BDO aggiunge \"temporanea\", senza affidarsi solo al colore.",
            "Temporary maintenance is easy to spot",
            "During a temporary maintenance the banner says \"Temporary maintenance in progress\" and the BDO tile "
            "adds \"temporary\", so it does not rely on colour alone.",
        ),
    ],
    "2.7.1": [
        Highlight(
            "INFO",
            "Manutenzioni ravvicinate non più nascoste",
            "Dopo la fine di una manutenzione ordinaria, il programma non mostrava l'avviso di un'altra manutenzione "
            "annunciata per il giorno dopo (per esempio una temporanea) fino a mezzanotte. Ora la mostra.",
            "Close-together maintenances no longer hidden",
            "After an ordinary maintenance had ended, the program did not show the notice of another maintenance "
            "announced for the next day (for example a temporary one) until midnight. Now it does.",
        ),
    ],
    "2.7": [
        Highlight(
            "GLOBE",
            "Orario della manutenzione preso dall'avviso ufficiale",
            "Il programma legge dall'avviso ufficiale l'orario e la durata reali, anche per le manutenzioni "
            "temporanee, e mostra \"In manutenzione, secondo l'avviso\" con il tempo rimasto. Se il sito non "
            "risponde usa una stima, corretta anche con il cambio d'ora.",
            "Maintenance time taken from the official notice",
            "The program reads the real time and duration from the official notice, including temporary "
            "maintenances, and shows \"Under maintenance, per the notice\" with the time left. If the site does not "
            "respond it uses an estimate, which is also correct across clock changes.",
        ),
        Highlight(
            "BRUSH",
            "Nuovi colori degli avvisi di manutenzione",
            "Arancione: manutenzione ordinaria annunciata. Rosso: manutenzione straordinaria o temporanea e "
            "qualunque manutenzione in corso. Lo stesso colore vale nel banner in cima alla dashboard e nel "
            "riquadro BDO.",
            "New colours for maintenance notices",
            "Orange: announced ordinary maintenance. Red: extraordinary or temporary maintenance, and any "
            "maintenance in progress. The same colour is used in the banner at the top of the dashboard and in the "
            "BDO tile.",
        ),
        Highlight(
            "ACCEPT",
            "Avviso verde a fine manutenzione",
            "Per 30 minuti dopo la fine compare un banner verde in alto: \"I server sono tornati online\", oppure "
            "\"dovrebbero essere tornati online\" se la fine è solo quella prevista. Se la manutenzione si "
            "allunga, nella scheda BDO c'è il pulsante \"+1 ora\".",
            "Green notice when maintenance ends",
            "For 30 minutes after the end a green banner appears at the top: \"The servers are back online\", or "
            "\"should be back online\" if the end is only the planned one. If the maintenance runs longer, the BDO "
            "tab has a \"+1 hour\" button.",
        ),
        Highlight(
            "SHOPPING_CART",
            "Manutenzioni del solo mercato",
            "Gli avvisi che riguardano solo il Central Market, il sito o i pagamenti non fanno più comparire "
            "\"In manutenzione\" per i server.",
            "Market-only maintenances",
            "Notices that only affect the Central Market, the website or payments no longer show \"Under "
            "maintenance\" for the servers.",
        ),
    ],
    "2.6": [
        Highlight(
            "GLOBE",
            "Stato dei server durante la manutenzione",
            "Il servizio esterno spesso segnalava i server online anche durante la manutenzione. Ora, nel giorno "
            "di una manutenzione annunciata, il programma mostra \"In manutenzione (stimata)\" negli orari previsti, "
            "con il tempo rimasto. Se dura di più, nella scheda BDO c'è \"+1 ora\". Gli orari si cambiano in Impostazioni.",
            "Server status during maintenance",
            "The external service often reported the servers as online even during maintenance. Now, on the day of "
            "an announced maintenance, the program shows \"Under maintenance (estimated)\" at the expected times, "
            "with the time left. If it lasts longer, the BDO tab has a \"+1 hour\" button. Times can be changed in "
            "Settings.",
        ),
        Highlight(
            "COPY",
            "Copia e incolla degli eventi del calendario",
            "Tasto destro su un evento → \"Copia evento\", poi tasto destro su un altro giorno → \"Incolla evento "
            "singolo\", \"Incolla serie\" (con la ripetizione) o \"Incolla e modifica\" per cambiare titolo o note. "
            "Dal menu di un giorno c'è anche \"Nuovo evento qui\".",
            "Copy and paste calendar events",
            "Right-click an event → \"Copy event\", then right-click another day → \"Paste single event\", \"Paste "
            "series\" (with repetition) or \"Paste and edit\" to change the title or notes. A day's menu also has "
            "\"New event here\".",
        ),
        Highlight(
            "SAVE",
            "Copia di sicurezza ogni notte",
            "Se lasci il programma aperto per giorni, alle 2 di notte ne fa da solo una copia di sicurezza, "
            "oltre a quella dell'avvio. Si tengono le ultime 30 e si ripristinano da Impostazioni → Backup.",
            "Safety backup every night",
            "If you leave the program open for days, at 2 a.m. it makes a safety backup by itself, in addition to "
            "the one at startup. The last 30 are kept and can be restored from Settings → Backup.",
        ),
    ],
}


def releases_to_show(last_seen: str | None, current: str, has_data: bool) -> list[str]:
    """Versioni di cui mostrare le novità, la più recente per prima.

    last_seen: ultima versione di cui l'utente ha già visto (o saltato) il popup; None se il
    programma non ha ancora memoria (primo avvio con questa funzione). In quel caso, se nel
    database ci sono già dati si tratta di un aggiornamento e si mostra solo l'ultima release
    (il resto non si può sapere); se è vuoto è un'installazione nuova e non c'è niente da
    raccontare. Se invece si ricorda l'ultima versione vista, si mostrano tutte le release
    uscite da allora fino a quella in uso (al massimo MAX_RELEASES_SHOWN): chi salta una
    versione non perde le sue novità. Mai per un ritorno a una versione più vecchia."""
    available = sorted((v for v in WHATS_NEW if version_key(v) <= version_key(current)), key=version_key, reverse=True)
    if last_seen is None:
        return available[:1] if has_data else []
    return [v for v in available if version_key(v) > version_key(last_seen)][:MAX_RELEASES_SHOWN]


def latest_release(current: str) -> str | None:
    """L'ultima release con novità non più recente della versione in uso."""
    available = sorted((v for v in WHATS_NEW if version_key(v) <= version_key(current)), key=version_key, reverse=True)
    return available[0] if available else None
