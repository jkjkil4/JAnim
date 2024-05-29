
from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QWidget


class FixedRatioWidget(QWidget):
    '''
    使得传入的 ``inside`` 控件可以以固定比例塞在该控件中
    '''
    def __init__(self, inside: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.inside = inside
        self.inside.setParent(self)
        self.src_size = (1, 1)

    def set_src_size(self, size: tuple[float, float]) -> None:
        self.src_size = size
        self.update_inner_size(self.size())

    def update_inner_size(self, wnd_size: QSize) -> None:
        wnd_width, wnd_height = wnd_size.toTuple()
        w, h = get_proportional_scale_size(*self.src_size, wnd_width, wnd_height)
        self.inside.setGeometry(
            (wnd_width - w) // 2,
            (wnd_height - h) // 2,
            w, h
        )

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.update_inner_size(event.size())


def get_proportional_scale_size(src_width, src_height, tg_width, tg_height):
    '''
    根据 ``(tg_width, tg_height)`` 的目标大小信息，
    得到 ``(src_width, src_height)`` 在进行等比缩放后能塞进目标区域的最大大小
    '''
    factor1 = tg_width / src_width
    factor2 = tg_height / src_height
    factor = min(factor1, factor2)
    return src_width * factor, src_height * factor
