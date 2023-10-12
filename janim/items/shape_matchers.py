from __future__ import annotations
from janim.typing import JAnimColor

from janim.constants import *
from janim.utils.margins import Margins, MarginsType
from janim.items.geometry.line import Line
from janim.items.geometry.polygon import Rectangle
from janim.items.item import Item

class SurroundingRectangle(Rectangle):
    def __init__(
        self, 
        item: Item, 
        *,
        buff: MarginsType = SMALL_BUFF,
        color: JAnimColor = YELLOW,
        width: float | None = None, 
        height: float | None = None, 
        **kwargs
    ):
        if not isinstance(buff, Margins):
            buff = Margins(buff)
        if width is None:
            width = item.get_width() + buff.left + buff.right
        if height is None:
            height = item.get_height() + buff.top + buff.bottom

        super().__init__(width, height, color=color, **kwargs)
        self.move_to(
            item.get_center() + [
                (buff.right - buff.left) / 2, 
                (buff.bottom - buff.top) / 2,
                0
            ]
        )

class Underline(Line):
    def __init__(self, item: Item, *, buff: float = SMALL_BUFF, **kwargs):
        super().__init__(LEFT, RIGHT, **kwargs)
        self.set_width(item.get_width())
        self.next_to(item, DOWN, buff=buff)
