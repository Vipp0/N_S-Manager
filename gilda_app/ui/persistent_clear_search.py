from qfluentwidgets import SearchLineEdit


class PersistentClearSearchLineEdit(SearchLineEdit):
    """SearchLineEdit con la X di cancellazione sempre visibile finché c'è del testo.

    Quello di qfluentwidgets nasconde la X appena il campo perde il focus e la mostra solo
    mentre ci si scrive: dopo una ricerca, per togliere il filtro bisognava prima cliccare
    nel campo. Qui la visibilità dipende solo dal fatto che ci sia del testo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setClearButtonEnabled(True)
        # Collegato dopo quello interno della libreria, quindi ha l'ultima parola.
        self.textChanged.connect(self._sync_clear_button)

    def _sync_clear_button(self, *_args) -> None:
        self.clearButton.setVisible(bool(self.text()))

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self._sync_clear_button()

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self._sync_clear_button()
