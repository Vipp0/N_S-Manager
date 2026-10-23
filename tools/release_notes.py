"""Note di release in formato GitHub (Markdown), generate dal changelog del programma.

Il changelog (gilda_app/changelog.py) è l'unica fonte delle novità: da qui escono sia quello che si
vede in Impostazioni sia le note delle Release su GitHub, così non si scrivono due volte e non
possono divergere.

Uso:
    python tools/release_notes.py 2.7.3                  # stampa le note della versione
    python tools/release_notes.py 2.7.3 --out note.md     # le scrive su file (UTF-8)
    gh release create v2.7.3 <zip> --title "v2.7.3" --notes-file note.md
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gilda_app.changelog import CHANGELOG  # noqa: E402
from gilda_app.whats_new import WHATS_NEW  # noqa: E402
from gilda_app.utils.update_check import version_key  # noqa: E402

# Dalla 2.2 il programma si aggiorna da solo (Impostazioni → Controlla aggiornamenti).
FIRST_SELF_UPDATING = "2.2"
MAX_LEAD_CHARS = 70


def format_note(note: str) -> str:
    """Una voce del changelog come punto elenco: se comincia con un titolo seguito da ":" lo si
    mette in grassetto ("Calendario: ..." -> "**Calendario**: ..."), e si chiude con un punto."""
    text = note.strip()
    head, sep, tail = text.partition(": ")
    if sep and len(head) <= MAX_LEAD_CHARS and "." not in head and head[:1].isupper() and tail:
        text = f"**{head}**: {tail}"
    if text[-1:] not in ".!?…)\"":
        text += "."
    return f"- {text}"


def build_notes(version: str) -> str:
    entry = next((e for e in CHANGELOG if e["version"] == version), None)
    if entry is None:
        raise SystemExit(f"Versione {version} non presente nel changelog")
    details = [format_note(note) for note in entry["notes"]]
    highlights = WHATS_NEW.get(version)
    if highlights:
        # Le versioni con il popup delle novità hanno già un riassunto breve e chiaro: si mostra quello,
        # e il dettaglio completo del changelog sta in una sezione che si apre con un clic.
        lines = ["## Novità in breve", ""]
        lines += [f"- **{h.title}**: {h.text}" for h in highlights]
        lines += ["", "<details>", "<summary>Dettaglio completo delle modifiche</summary>", ""]
        lines += details
        lines += ["", "</details>"]
    else:
        lines = ["## Cosa cambia", ""]
        lines += details
    lines += ["", "## Come aggiornare", ""]
    if version_key(version) >= version_key(FIRST_SELF_UPDATING):
        lines += [
            "- **Dal programma** (da una versione 2.2 o successiva): all'avvio propone l'aggiornamento, oppure "
            "**Impostazioni → Controlla aggiornamenti**. Prima di installare fa una copia di sicurezza del database.",
            "- **A mano** (da una versione precedente): chiudi il programma, scarica lo zip qui sotto ed estrailo "
            "sopra la cartella del programma, sostituendo i file.",
        ]
    else:
        lines += [
            "- Chiudi il programma, scarica lo zip qui sotto ed estrailo sopra la cartella del programma, "
            "sostituendo i file.",
        ]
    lines += [
        "",
        "---",
        "Lo zip contiene solo il programma: `gilda.db`, `backups` e `errori.log` non sono inclusi e non vengono "
        "toccati. L'impronta SHA256 del file è mostrata da GitHub accanto allo zip.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("version", help="versione, senza la v (es. 2.7.3)")
    parser.add_argument("--out", help="file di destinazione (UTF-8); senza, stampa a video")
    args = parser.parse_args()
    notes = build_notes(args.version.lstrip("vV"))
    if args.out:
        Path(args.out).write_text(notes, encoding="utf-8", newline="\n")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(notes)


if __name__ == "__main__":
    main()
