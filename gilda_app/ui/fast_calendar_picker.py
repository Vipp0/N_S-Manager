from PySide6.QtCore import QDate, QPoint, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QHBoxLayout, QWidget
from qfluentwidgets import CalendarPicker, LineEdit
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


class _CalendarIconButton(FastCalendarPicker):
    """FastCalendarPicker ridotto alla sola icona, senza testo: usato dentro DateEdit
    accanto al campo scrivibile, dove il testo del bottone (la data formattata)
    ripeterebbe quello già mostrato nel campo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("")
        self.setFixedWidth(34)

    def _onDateChanged(self, date: QDate) -> None:
        self._date = QDate(date)
        self.setProperty("hasDate", True)
        self.setStyle(QApplication.style())
        self.update()
        self.dateChanged.emit(date)


class DateEdit(QWidget):
    """Campo data: si può scrivere a mano (dd-mm-yyyy) oppure scegliere dal
    calendarietto accanto, invece di poter usare solo quest'ultimo come con
    FastCalendarPicker da solo. Utile per inserire in fretta molte date storiche
    (vedi RebuildHistoryDialog) senza dover aprire il calendario ogni volta.
    """

    dateChanged = Signal(QDate)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._line = LineEdit(self)
        # Maschera a griglia di cifre: impedisce di scrivere caratteri non numerici,
        # ma non valida date inesistenti (es. 31-02) - quello avviene alla conferma.
        self._line.setInputMask("00-00-0000;_")
        self._line.editingFinished.connect(self._on_text_edited)

        self._icon_btn = _CalendarIconButton(self)
        self._icon_btn.dateChanged.connect(self._on_picker_changed)

        layout.addWidget(self._line, 1)
        layout.addWidget(self._icon_btn)

        self._date = QDate()

    def getDate(self) -> QDate:
        return self._date

    def setDate(self, date: QDate) -> None:
        self._date = QDate(date)
        # Sincronizza il bottone-icona senza passare da setDate: emetterebbe dateChanged
        # e richiamerebbe questo stesso metodo di rimbalzo.
        self._icon_btn._date = QDate(date)
        self._icon_btn.setProperty("hasDate", date.isValid())
        self._icon_btn.setStyle(QApplication.style())
        self._refresh_text()

    def _refresh_text(self) -> None:
        self._line.setText(self._date.toString(DISPLAY_DATE_QT_FORMAT) if self._date.isValid() else "")

    def _on_text_edited(self) -> None:
        date = QDate.fromString(self._line.text(), DISPLAY_DATE_QT_FORMAT)
        if date.isValid():
            self.setDate(date)
            self.dateChanged.emit(date)
        else:
            # testo incompleto o data inesistente (es. 31-02): torna all'ultima valida
            self._refresh_text()

    def _on_picker_changed(self, date: QDate) -> None:
        self._date = QDate(date)
        self._refresh_text()
        self.dateChanged.emit(date)
