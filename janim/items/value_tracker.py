
import copy
from typing import Self

from janim.components.component import CmptInfo
from janim.components.data import Cmpt_Data, CopyFn, NotChangedFn, InterpolateFn
from janim.items.item import Item
from janim.utils.bezier import interpolate


class ValueTracker[T](Item):
    '''
    记录一个数值数据（传入的数据作为初始值），可以进行动画插值

    例如：

    .. code-block:: python

        val = ValueTracker(0.5)

        self.play(
            val.anim.data.set(3.5),
            DataUpdater(...)
        )

    可以使用 :meth:`~.Cmpt_Data.set_func` 自定义插值以及其它的行为
    '''

    data = CmptInfo(Cmpt_Data[Self, T])

    def __init__(
        self,
        value: T,
        copy_func: CopyFn[T] = copy.copy,
        not_changed_func: NotChangedFn[T] = lambda a, b: a == b,
        interpolate_func: InterpolateFn[T] = interpolate,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.data.set_func(copy_func, not_changed_func, interpolate_func)
        self.data.set(value)

        if self.timeline is not None:
            # 使得 ValueTracker 的内容更改哪怕没有 show 和 anim 也可以被跟踪
            self.timeline.item_appearances[self]
