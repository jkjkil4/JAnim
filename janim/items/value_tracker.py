from typing import Self

from janim.components.component import CmptInfo
from janim.components.data import Cmpt_Data
from janim.items.item import Item


class ValueTracker[T](Item):
    """
    记录一个数值数据（传入的数据作为初始值），可以进行动画插值

    例如：

    .. code-block:: python

        tr = ValueTracker(0.5)

        self.play(
            tr.anim.set_value(3.5),
            DataUpdater(...)
        )

    详情另见文档 :ref:`基础用法 <value_tracker_basic>` 中对 :class:`ValueTracker` 用法的介绍
    """

    _data = CmptInfo(Cmpt_Data[Self, T])

    def __init__(
        self,
        value: T,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._data.set(value)

        if self.timeline is not None:
            # 使得 ValueTracker 的内容更改哪怕没有 show 和 anim 也可以被跟踪
            self.timeline.track(self)

    def set_value(self, value: T) -> Self:
        """设置当前值"""
        self._data.set(value)
        return self

    def get_value(self) -> T:
        """得到当前值"""
        return self._data.get()

    def increment(self, value: T) -> Self:
        """将值增加 ``value``，只对一些简单的类型有效"""
        self._data.increment(value)
        return self

    def update_value(self, patch: T) -> Self:
        """基于字典的部分项更新原有字典"""
        self._data.update(patch)
        return self
