import os
import subprocess
import sys

from PySide6.QtWidgets import QApplication


def restart_app() -> None:
    """Nasconde le finestre, avvia una nuova istanza e chiude quella corrente.

    os.execv su Windows non sostituisce il processo: il vecchio restava visibile per
    qualche secondo accanto al nuovo. Qui la finestra sparisce subito e resta solo lo
    splash della nuova istanza."""
    app = QApplication.instance()
    for widget in app.topLevelWidgets():
        widget.hide()
    args = [sys.executable] + (sys.argv[1:] if getattr(sys, "frozen", False) else sys.argv)
    env = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT="1")
    subprocess.Popen(args, env=env, close_fds=True)
    app.quit()
