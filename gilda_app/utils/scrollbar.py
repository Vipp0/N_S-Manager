"""Scrollbar di qfluentwidgets più spessa al passaggio del mouse.

Di default l'handle passa da 3px a un massimo di 6px al hover (vedi
ScrollBarHandle/_onOpacityAniValueChanged in qfluentwidgets), che nella pratica
resta comunque sottile e difficile da afferrare col cursore. Non esiste
un'opzione pubblica per configurarlo, quindi si scollega il calcolo di
larghezza di default e se ne aggancia uno con margini più larghi, restando
comunque entro i 12px del binario della scrollbar per non tagliare l'handle."""
from PySide6.QtCore import Qt


def widen_scrollbar_on_hover(scrollbar, base_width: int = 4, hover_extra: int = 5) -> None:
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
