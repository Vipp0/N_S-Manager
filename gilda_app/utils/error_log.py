"""Registro degli errori imprevisti: un file "errori.log" accanto al programma.

Nell'eseguibile non c'è una console, quindi un errore non gestito sparirebbe senza lasciare
traccia. Qui ogni eccezione non gestita (anche nei thread) e ogni arresto brusco del
programma si scrivono nel file, con data e versione, così chi riceve la segnalazione può
chiedere di mandarlo. Il file si tiene piccolo da solo."""
import faulthandler
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path

LOG_NAME = "errori.log"
MAX_BYTES = 256 * 1024

_crash_file = None  # deve restare aperto finché il programma gira, per faulthandler


def _trim(path: Path) -> None:
    """Oltre il limite si tengono solo le ultime voci (la metà finale del file)."""
    try:
        if path.stat().st_size <= MAX_BYTES:
            return
        data = path.read_bytes()[-MAX_BYTES // 2:]
        newline = data.find(b"\n")
        path.write_bytes(data[newline + 1:] if newline >= 0 else data)
    except OSError:
        pass


def write_entry(path: Path, version: str, title: str, details: str) -> None:
    """Aggiunge una voce al registro. Non solleva mai: scrivere l'errore non deve crearne un altro."""
    try:
        stamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        with open(path, "a", encoding="utf-8") as out:
            out.write(f"[{stamp}] v{version} - {title}\n{details.rstrip()}\n\n")
        _trim(path)
    except Exception:
        pass


def install(path: Path, version: str) -> None:
    """Da chiamare una volta all'avvio."""
    global _crash_file
    previous_hook = sys.excepthook

    def excepthook(exc_type, exc, tb):
        write_entry(path, version, "errore non gestito", "".join(traceback.format_exception(exc_type, exc, tb)))
        try:
            previous_hook(exc_type, exc, tb)
        except Exception:
            pass

    def thread_hook(args):
        if args.exc_type is SystemExit:
            return
        name = args.thread.name if args.thread else "?"
        write_entry(
            path,
            version,
            f"errore non gestito nel thread {name}",
            "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)),
        )

    sys.excepthook = excepthook
    threading.excepthook = thread_hook
    try:
        _crash_file = open(path, "a", encoding="utf-8")
        faulthandler.enable(_crash_file)  # arresto brusco (crash nativo): scrive lo stato dei thread
    except (OSError, RuntimeError):
        _crash_file = None
