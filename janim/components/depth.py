from __future__ import annotations

import numbers
from collections import defaultdict
from typing import Self

from janim.anims.method_updater_meta import register_updater
from janim.components.component import Component
from janim.utils.bezier import interpolate
from janim.utils.data import AlignedData


class Cmpt_Depth[ItemT](Component[ItemT]):
    '''深度组件

    - 如果某个对象的深度值更小，那么它在 ``>`` 和 ``<`` 的判断中也就更小
    - 如果两个对象的深度值相同，那么后创建的对象在 ``>`` 和 ``<`` 的判断中更小

    被用于绘制时，也就是说：

    - 深度大的会被深度小的遮盖
    - 深度一样时，先创建的会被后创建的遮盖

    例：

    .. code-block:: python

        d1 = Depth(0)
        d2 = Depth(2)
        d3 = Depth(2)

        print(d1 < d3)  # True
        print(d2 < d3)  # False
        print(d2 > d3)  # True

    上面这个例子的绘制顺序（从最早被绘制的到最迟被绘制的）：

    d2、d3、d1

    也就是 d3 会盖住 d2；d1 会盖住 d2 和 d3
    '''
    _counter: defaultdict[float, int] = defaultdict(int)

    def __init__(self, value: float, order: int | None = None):
        super().__init__()

        # 相当于 self.set(value, order, root_only=True)
        self._depth = value
        if order is None:
            self._order = self._counter[value]
            self._counter[value] -= 1
        else:
            self._order = order

    def copy(self) -> Self:
        # Component.copy 中的 copy.copy(self) 已将 _value 和 _order 拷贝
        return super().copy()

    def become(self, other: Cmpt_Depth) -> Self:
        self._depth = other._depth
        self._order = other._order
        return self

    def not_changed(self, other: Cmpt_Depth) -> bool:
        return self._depth == other._depth and self._order == other._order

    @classmethod
    def align_for_interpolate(cls, cmpt1: Cmpt_Depth, cmpt2: Cmpt_Depth):
        cmpt1_copy = cmpt1.copy()
        cmpt2_copy = cmpt2.copy()
        return AlignedData(cmpt1_copy, cmpt2_copy, cmpt1_copy.copy())

    def interpolate(self, cmpt1: Cmpt_Depth, cmpt2: Cmpt_Depth, alpha: float, *, path_func=None) -> None:
        d1, o1 = cmpt1.get_raw()
        d2, o2 = cmpt2.get_raw()
        self.set(interpolate(d1, d2, alpha), interpolate(o1, o2, alpha), root_only=True)

    def __lt__(self, other: Cmpt_Depth) -> bool:
        if self._depth != other._depth:
            return self._depth < other._depth
        return self._order < other._order

    def _set_updater(self, p, value, order=None, *, root_only: bool = False) -> None:
        if order is None:
            order = self._order
        self._depth = interpolate(self._depth, value, p.alpha)
        self._order = interpolate(self._order, order, p.alpha)

    @register_updater(_set_updater)
    def set(self, value: float, order: int | None = None, *, root_only: bool = False) -> Self:
        '''
        设置物件的深度
        '''
        assert isinstance(value, numbers.Real)

        if order is None:
            order = self._counter[value]
            for cmpt in self.walk_same_cmpt_of_self_and_descendants_without_mock(root_only):
                cmpt._depth = value
                cmpt._order = order
                order -= 1
            self._counter[value] = order
        else:
            for cmpt in self.walk_same_cmpt_of_self_and_descendants_without_mock(root_only):
                cmpt._depth = value
                cmpt._order = order

        return self

    def get(self) -> float:
        return self._depth

    def get_raw(self) -> tuple[float, int | float]:
        '''
        返回元组 ``(depth, order)``

        在一些特殊情况下，``order`` 可能是浮点数
        '''
        return (self._depth, self._order)

    def arrange(self, depth: float | None = None) -> Self:
        '''
        将子物件排序深度
        '''
        if depth is None:
            depth = self._depth
        self.set(depth)
        return self
