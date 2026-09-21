from PySide6.QtCore import QPoint, Qt, QTimer
from qfluentwidgets import CalendarPicker
from qfluentwidgets.components.date_time.calendar_view import CalendarView

from gilda_app.utils.date_format import DISPLAY_DATE_QT_FORMAT


class FastCalendarPicker(CalendarPicker):
    """CalendarPicker che apre il calendario istantaneamente al click.

    Il CalendarPicker di qfluentwidgets ricostruisce da zero l'intera CalendarView
    (viste anno/mese/giorno con tutti i loro item) ad ogni click: ~600ms di blocco
    dell'interfaccia, che rendevano l'apertura lenta e a volte non reattiva a click
    ripetuti. Qui la view viene costruita una sola volta e riusata, e mostrata senza
    animazione, così compare subito. Viene anche pre-costruita poco dopo che il picker
    è comparso (mentre l'utente legge/compila il resto del form), così anche il primo
    click è immediato invece di pagare i ~600ms di costruzione.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Il testo del pulsante mostra la data come dd-mm-yyyy (il valore restituito da
        # getDate() è comunque un QDate: il formato di salvataggio lo decide chi lo legge).
        self.setDateFormat(DISPLAY_DATE_QT_FORMAT)
        self._view: CalendarView | None = None
        self._prewarm_scheduled = False

    def showEvent(self, event):
        super().showEvent(event)
        if not self._prewarm_scheduled:
            self._prewarm_scheduled = True
            # Ritardo maggiore dell'animazione di apertura del dialog, così non la si
            # blocca: alla fine dell'apertura la view è pronta e il primo click è
            # immediato. Se l'utente clicca prima, _ensure_view la costruisce comunque.
            QTimer.singleShot(300, self._ensure_view)

    def _ensure_view(self) -> CalendarView:
        if self._view is None:
            view = CalendarView(self.window())
            # Di default la view ha WA_DeleteOnClose: verrebbe distrutta alla chiusura
            # e ricostruita (di nuovo ~600ms) al click successivo. La teniamo viva così
            # dal secondo click in poi l'apertura è immediata. I segnali si collegano
            # una sola volta, non ad ogni apertura come fa la classe base.
            view.setAttribute(Qt.WA_DeleteOnClose, False)
            view.setResetEnabled(self.isRestEnabled())
            view.resetted.connect(self.reset)
            view.dateChanged.connect(self._onDateChanged)
            self._view = view
        return self._view

    def _showCalendarView(self):
        view = self._ensure_view()
        if self.date.isValid():
            view.setDate(self.date)
        x = int(self.width() / 2 - view.sizeHint().width() / 2)
        y = self.height()
        view.exec(self.mapToGlobal(QPoint(x, y)), ani=False)
