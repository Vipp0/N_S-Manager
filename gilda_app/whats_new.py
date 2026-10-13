"""Novità mostrate in un popup al primo avvio dopo un aggiornamento.

Una voce per ogni release pubblicata (non per le versioni intermedie), scritta per chi usa il
programma: poche voci, ognuna con un titolo breve e una frase chiara, senza termini tecnici.
Ci vanno le funzioni nuove e i difetti che l'utente poteva davvero incontrare nella versione
che aveva prima; un difetto nato e corretto tra due release non si cita mai, perché nessuno
l'ha visto. Il dettaglio completo resta in changelog.py."""
from dataclasses import dataclass

from gilda_app.utils.update_check import version_key

MAX_RELEASES_SHOWN = 3


@dataclass(frozen=True)
class Highlight:
    icon: str  # nome di un'icona di qfluentwidgets.FluentIcon (es. "CALENDAR")
    title: str
    text: str


# Chiave: versione della release (come in version.py, es. "2.6").
WHATS_NEW: dict[str, list[Highlight]] = {
    "2.6": [
        Highlight(
            "GLOBE",
            "Stato dei server durante la manutenzione",
            "Il servizio esterno spesso segnalava i server online anche durante la manutenzione. Ora, nel giorno "
            "di una manutenzione annunciata, il programma mostra \"In manutenzione (stimata)\" negli orari previsti, "
            "con il tempo rimasto. Se dura di più, nella scheda BDO c'è \"+1 ora\". Gli orari si cambiano in Impostazioni.",
        ),
        Highlight(
            "COPY",
            "Copia e incolla degli eventi del calendario",
            "Tasto destro su un evento → \"Copia evento\", poi tasto destro su un altro giorno → \"Incolla evento "
            "singolo\", \"Incolla serie\" (con la ripetizione) o \"Incolla e modifica\" per cambiare titolo o note. "
            "Dal menu di un giorno c'è anche \"Nuovo evento qui\".",
        ),
        Highlight(
            "SAVE",
            "Copia di sicurezza ogni notte",
            "Se lasci il programma aperto per giorni, alle 2 di notte ne fa da solo una copia di sicurezza, "
            "oltre a quella dell'avvio. Si tengono le ultime 30 e si ripristinano da Impostazioni → Backup.",
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
