"""Scrollbar di qfluentwidgets più spessa e centrata al passaggio del mouse.

Di default l'handle passa da 3px a un massimo di 6px al hover (vedi
ScrollBarHandle/_onOpacityAniValueChanged in qfluentwidgets), che nella pratica
resta comunque sottile e difficile da afferrare col cursore. Non esiste
un'opzione pubblica per configurarlo, quindi si scollega il calcolo di
larghezza di default e se ne aggancia uno con margini più larghi, restando
comunque entro i 12px del binario della scrollbar per non tagliare l'handle.

qfluentwidgets calcola la posizione orizzontale dell'handle ancorandolo al
bordo destro del binario (x = larghezza_binario - larghezza_handle - 3): con
l'handle più spesso questo lo fa crescere solo verso sinistra, sfasandolo
rispetto alle freccette su/giù (che invece sono centrate nel binario). Si
sostituisce quindi anche _adjustHandlePos con una versione che centra
l'handle, mantenendo identico il resto della logica (posizione verticale in
base allo scroll)."""
from types import MethodType

from PySide6.QtCore import Qt


def widen_scrollbar_on_hover(scrollbar, base_width: int = 4, hover_extra: int = 5) -> None:
    def _adjust_handle_pos(self) -> None:
        total = max(self.maximum() - self.minimum(), 1)
        delta = int(self.value() / total * self._slideLength())
        if self.orientation() == Qt.Vertical:
            x = (self.width() - self.handle.width()) // 2
            self.handle.move(x, self._padding + delta)
        else:
            y = (self.height() - self.handle.height()) // 2
            self.handle.move(self._padding + delta, y)

    scrollbar._adjustHandlePos = MethodType(_adjust_handle_pos, scrollbar)

    def _on_opacity_changed(_value=None):
        opacity = scrollbar.groove.opacity
        width = int(base_width + opacity * hover_extra)
        if scrollbar.orientation() == Qt.Vertical:
            scrollbar.handle.setFixedWidth(width)
        else:
            scrollbar.handle.setFixedHeight(width)
        scrollbar._adjustHandlePos()

    scrollbar.groove.opacityAni.valueChanged.disconnect(scrollbar._onOpacityAniValueChanged)
    scrollbar.groove.opacityAni.valueChanged.connect(_on_opacity_changed)
