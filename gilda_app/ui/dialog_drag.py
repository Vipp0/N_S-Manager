"""Rende spostabile il riquadro di un dialogo qfluentwidgets (MessageBoxBase).

Questi dialoghi sono un riquadro centrato sopra l'intera finestra del programma, che resta
visibile ma attenuata: spostando il riquadro di lato si può leggere quello che c'è sotto
(non cliccarlo: il dialogo resta modale). Si trascina dal titolo o da qualunque punto non
interattivo del riquadro (bordi, spazi tra i campi).

Lo spostamento vive solo nell'oggetto DialogDragger, che appartiene al dialogo: i dialoghi
si creano da zero a ogni apertura, quindi si riaprono sempre al centro, senza memoria."""
from PySide6.QtCore import QEvent, QObject, QPoint, QSize, Qt


class DialogDragger(QObject):
    def __init__(self, dialog, title_widget=None):
        super().__init__(dialog)
        self._dialog = dialog
        self._layout = dialog._hBoxLayout  # non è API pubblica di qfluentwidgets: sotto, si degrada
        self._base = self._layout.contentsMargins()
        self._offset = QPoint(0, 0)
        self._press_global: QPoint | None = None
        self._press_offset = QPoint(0, 0)
        dialog.widget.installEventFilter(self)
        dialog.installEventFilter(self)  # per ri-limitare lo scarto se la finestra si rimpicciolisce
        if title_widget is not None:
            title_widget.setCursor(Qt.SizeAllCursor)

    @property
    def offset(self) -> QPoint:
        return QPoint(self._offset)

    def _clamped(self, offset: QPoint, window: QSize) -> QPoint:
        """Il riquadro deve restare tutto dentro la finestra. Si misura la sua dimensione
        naturale, non quella attuale: spingendolo contro un bordo il layout lo schiaccia per
        farcelo stare, e con la misura schiacciata si crederebbe di avere ancora spazio."""
        card = self._dialog.widget.sizeHint().expandedTo(self._dialog.widget.minimumSize())
        slack_x = max(0, (window.width() - card.width()) // 2 - max(self._base.left(), self._base.right()))
        slack_y = max(0, (window.height() - card.height()) // 2 - max(self._base.top(), self._base.bottom()))
        return QPoint(max(-slack_x, min(slack_x, offset.x())), max(-slack_y, min(slack_y, offset.y())))

    def _apply(self, offset: QPoint, window: QSize | None = None) -> None:
        self._offset = self._clamped(offset, window or self._dialog.size())
        # Il riquadro è centrato dal layout: per spostarlo di dx basta sbilanciare i margini
        # di 2*dx (il centro si sposta di metà della differenza). Così il layout resta in
        # carica e ridimensionamenti e cambi di contenuto continuano a funzionare.
        b, o = self._base, self._offset
        self._layout.setContentsMargins(
            b.left() + max(0, 2 * o.x()),
            b.top() + max(0, 2 * o.y()),
            b.right() + max(0, -2 * o.x()),
            b.bottom() + max(0, -2 * o.y()),
        )
        self._layout.activate()

    def eventFilter(self, obj, event) -> bool:
        kind = event.type()
        if obj is self._dialog:
            if kind == QEvent.Resize and not self._offset.isNull():
                self._apply(self._offset, event.size())
            return False
        # Qui arrivano solo i click che nessun campo/pulsante ha preso per sé.
        if kind == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self._press_global = event.globalPosition().toPoint()
            self._press_offset = QPoint(self._offset)
            event.accept()
            return True
        if kind == QEvent.MouseMove and self._press_global is not None and event.buttons() & Qt.LeftButton:
            self._apply(self._press_offset + event.globalPosition().toPoint() - self._press_global)
            return True
        if kind == QEvent.MouseButtonRelease and self._press_global is not None:
            self._press_global = None
            return True
        return False


def make_draggable(dialog, title_widget=None) -> None:
    """Attiva il trascinamento sul dialogo; se qfluentwidgets cambiasse la sua struttura
    interna il dialogo resta semplicemente fisso al centro, come prima."""
    try:
        DialogDragger(dialog, title_widget)
    except AttributeError:
        pass
