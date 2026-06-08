from janim.anims_core.stackable import ApplyParams, StackableAnimation
from janim.items.item import Item


class Display(StackableAnimation):
    """
    用于标记物件在特定时间区段中的数据

    作为 :meth:`~.AnimStack.display` 的产物，表示“物件从一个特定时间开始，被更改为了这样的数据”

    另见：:meth:`~.Timeline.detect_changes_of_all`
    """

    def __init__(self, data: Item, **kwargs):
        super().__init__(**kwargs)
        self.data = data
        self.data_orig = data.store()

    def apply(self, params: ApplyParams) -> None:
        """
        给 ``params`` 初始化物件数据

        将 ``self.data`` 重置为 ``self.data_orig`` 的数据并设置到 ``params.data`` 上，避免原始数据被意外更改

        特殊情况：

        当 :class:`~.AnimStack` 的动画堆栈只有一个动画，即该动画 :class:`Display` 时，不会经由该方法，
        而是直接被其访问 ``data_orig``，起到一点点优化的作用
        """
        self.data.restore(self.data_orig)
        params.data = self.data
