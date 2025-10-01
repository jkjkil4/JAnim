from __future__ import annotations

from typing import Self

from janim.components.component import Component
from janim.utils.bezier import interpolate
from janim.utils.data import AlignedData


class Cmpt_Float[ItemT](Component[ItemT]):
    '''
    对 float 的 Component 封装
    '''
    def __init__(self, default_value, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = default_value

    def copy(self) -> Self:
        return Component.copy(self)

    def become(self, other: Cmpt_Float) -> Self:
        self._value = other._value

    def not_changed(self, other: Cmpt_Float) -> Self:
        return self._value == other._value

    @classmethod
    def align_for_interpolate(cls, cmpt1: Cmpt_Float, cmpt2: Cmpt_Float):
        cmpt1_copy = cmpt1.copy()
        cmpt2_copy = cmpt2.copy()
        return AlignedData(cmpt1_copy, cmpt2_copy, cmpt1_copy.copy())

    def interpolate(self, cmpt1: Cmpt_Float, cmpt2: Cmpt_Float, alpha: float, *, path_func=None) -> None:
        if cmpt1._value != cmpt2._value or cmpt1._value != self._value:
            self._value = interpolate(cmpt1._value, cmpt2._value, alpha)

    def set(self, value: float) -> Self:
        self._value = value
        return self

    def get(self) -> float:
        return self._value


class Cmpt_List[ItemT, T](list[T], Component[ItemT]):
    def copy(self) -> Self:
        return Component.copy(self)

    def become(self, other: Cmpt_List) -> Self:
        self.clear()
        self.extend(other)
        return self

    def not_changed(self, other: Cmpt_List) -> Self:
        return self == other


class Cmpt_Dict[ItemT, K, V](dict[K, V], Component[ItemT]):
    def copy(self) -> Self:
        return Component.copy(self)

    def become(self, other: Cmpt_Dict) -> Self:
        self.clear()
        self.update(other)
        return self

    def not_changed(self, other: Cmpt_Dict) -> Self:
        return self == other
