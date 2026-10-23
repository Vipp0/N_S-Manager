"""Applicazione Qt condivisa dai test che toccano Qt: ne basta una per tutta la sessione, e deve
essere una QApplication (con i widget) anche per i test che userebbero solo QtCore, altrimenti
chi viene dopo trova un'applicazione senza widget e il processo si chiude di colpo."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])
