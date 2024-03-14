
import copy
from typing import Self

from janim.components.component import CmptInfo
from janim.components.data import Cmpt_Data, CopyFn, EqFn, InterpolateFn
from janim.items.item import Item
from janim.utils.bezier import interpolate


class ValueTracker[T](Item):
    data = CmptInfo(Cmpt_Data[Self, T])

    def __init__(
        self,
        value: T,
        copy_func: CopyFn[T] = copy.copy,
        eq_func: EqFn[T] = lambda a, b: a == b,
        interpolate_func: InterpolateFn[T] = interpolate,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.data.set_func(copy_func, eq_func, interpolate_func)
        self.data.set(value)
