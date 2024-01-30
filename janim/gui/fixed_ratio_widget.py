
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QWidget


class FixedRatioWidget(QWidget):
    def __init__(self, inside: QWidget, src_size: tuple[float, float], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.inside = inside
        self.inside.setParent(self)
        self.src_size = src_size

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)

        wnd_width, wnd_height = event.size().toTuple()
        w, h = get_proportional_scale_size(*self.src_size, wnd_width, wnd_height)
        self.inside.setGeometry((wnd_width - w) // 2,
                                (wnd_height - h) // 2,
                                w, h)


def get_proportional_scale_size(src_width, src_height, tg_width, tg_height):
    factor1 = tg_width / src_width
    factor2 = tg_height / src_height
    factor = min(factor1, factor2)
    return src_width * factor, src_height * factor
