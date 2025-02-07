from janim.anims.animation import ItemAnimation
from janim.items.item import Item


class Display(ItemAnimation):
    '''
    用于标记物件在特定时间区段中的数据

    一般作为 :meth:`~.AnimStack.detect_change` 的产物，表示“物件从一个特定时间开始，被更改为了这样的数据”

    另见：:meth:`~.Timeline.detect_changes_of_all`
    '''
    def __init__(self, item: Item, data: Item, **kwargs):
        super().__init__(item, **kwargs)
        self._cover_previous_anims = True
        self.data = data
        self.data_orig = data.store()

    def apply(self, data: None, p: ItemAnimation.ApplyParams) -> Item:
        '''
        返回记录的物件数据

        - 如果 ``p.anims`` 只有一个元素（也就是自己），那么可以认为返回值不会再次被更改，因此直接返回 ``self.data_orig``
        - 如果 ``p.anims`` 不止一个元素，那么将 ``self.data`` 重置为 ``self.data_orig`` 的数据并返回，避免 ``self.data_orig`` 被意外更改
        '''
        if len(p.anims) == 1:
            return self.data_orig

        self.data.restore(self.data_orig)
        return self.data
