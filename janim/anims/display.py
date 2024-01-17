from typing import TYPE_CHECKING

from janim.anims.animation import Animation

if TYPE_CHECKING:   # pragma: no cover
    from janim.items.item import Item


class Display(Animation):
    def __init__(self, item: 'Item', **kwargs):
        super().__init__(**kwargs)
        self.item = item
