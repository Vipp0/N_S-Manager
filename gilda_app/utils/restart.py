import os
import sys


def restart_app() -> None:
    """Rilancia lo stesso eseguibile/script sostituendo il processo corrente."""
    python = sys.executable
    os.execv(python, [python] + sys.argv)
