from typing import TYPE_CHECKING

from janim.anims.animation import Animation

if TYPE_CHECKING:   # pragma: no cover
    from janim.items.item import Item


class Display(Animation):
    '''
    在指定的时间区间上显示物件
    '''
    def __init__(self, item: 'Item', root_only=False, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self.root_only = root_only
