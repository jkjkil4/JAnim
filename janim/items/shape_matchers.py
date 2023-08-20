from __future__ import annotations
from typing import Optional

from janim.constants import *
from janim.items.geometry.line import Line
from janim.items.geometry.polygon import Rectangle
from janim.items.item import Item

class SurroundingRectangle(Rectangle):
    def __init__(
        self, 
        item: Item, 
        buff: float = SMALL_BUFF,
        color: JAnimColor = YELLOW,
        width: Optional[float] = None, 
        height: Optional[float] = None, 
        **kwargs
    ):
        if width is None:
            width = item.get_width() + 2 * buff
        if height is None:
            height = item.get_height() + 2 * buff

        super().__init__(width, height, color=color, **kwargs)
        self.move_to(item)

class Underline(Line):
    def __init__(self, item: Item, buff: float = SMALL_BUFF, **kwargs):
        super().__init__(LEFT, RIGHT, **kwargs)
        self.set_width(item.get_width())
        self.next_to(item, DOWN, buff=buff)
