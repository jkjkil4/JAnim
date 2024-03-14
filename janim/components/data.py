from __future__ import annotations

from typing import Callable, Self

from janim.components.component import Component
from janim.utils.data import AlignedData

type CopyFn[T] = Callable[[T], T]
type EqFn[T] = Callable[[T, T], bool]
type InterpolateFn[T] = Callable[[T, T, float], T]


class Cmpt_Data[ItemT, T](Component[ItemT]):
    '''
    详见 :class:`~.ValueTracker`
    '''
    def __init__(self):
        self.copy_func: CopyFn[T] = None
        self.eq_func: EqFn[T] = None
        self.interpolate_func: InterpolateFn[T] = None

    def copy(self) -> Self:
        cmpt_copy = super().copy()

        assert self.copy_func is not None
        cmpt_copy.set(self.copy_func(self.value))

        return cmpt_copy

    def become(self, other: Cmpt_Data) -> Self:
        self.set(other.copy_func(other.value))
        return self

    def __eq__(self, other: Cmpt_Data) -> bool:
        assert self.eq_func is not None
        return self.eq_func(self.value, other.value)

    @classmethod
    def align_for_interpolate(cls, cmpt1: Cmpt_Data, cmpt2: Cmpt_Data) -> AlignedData[Self]:
        cmpt1_copy = cmpt1.copy()
        cmpt2_copy = cmpt2.copy()
        return AlignedData(cmpt1_copy, cmpt2_copy, cmpt1_copy.copy())

    def interpolate(self, cmpt1: Cmpt_Data, cmpt2: Cmpt_Data, alpha: float, *, path_func=None) -> Self:
        if cmpt1 == cmpt2:
            return

        self.set(self.interpolate_func(cmpt1.value, cmpt2.value, alpha))
        return self

    def set(self, value: T) -> Self:
        '''设置当前数据'''
        self.value = value
        return self

    def increment(self, value: T) -> Self:
        '''将值增加 ``value``'''
        self.value += value
        return self

    def get(self) -> T:
        '''得到当前数据'''
        return self.value

    def set_func(
        self,
        copy_func: CopyFn[T] | None = None,
        eq_func: EqFn[T] | None = None,
        interpolate_func: InterpolateFn[T] | None = None
    ) -> Self:
        if copy_func is not None:
            self.copy_func = copy_func
        if eq_func is not None:
            self.eq_func = eq_func
        if interpolate_func is not None:
            self.interpolate_func = interpolate_func
        return self
