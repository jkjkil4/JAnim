from __future__ import annotations

from typing import Callable, Self

from janim.components.component import Component
from janim.utils.data import AlignedData

type CopyFn[T] = Callable[[T], T]
type NotChangedFn[T] = Callable[[T, T], bool]
type InterpolateFn[T] = Callable[[T, T, float], T]


class Cmpt_Data[ItemT, T](Component[ItemT]):
    '''
    详见 :class:`~.ValueTracker`
    '''
    def __init__(self):
        self.copy_func: CopyFn[T] = None
        self.not_changed_func: NotChangedFn[T] = None
        self.interpolate_func: InterpolateFn[T] = None

    def copy(self) -> Self:
        cmpt_copy = super().copy()

        assert self.copy_func is not None
        cmpt_copy.set(self.copy_func(self.value))

        return cmpt_copy

    def become(self, other: Cmpt_Data) -> Self:
        self.set(other.copy_func(other.value))
        return self

    def not_changed(self, other: Cmpt_Data) -> bool:
        assert self.not_changed_func is not None
        return self.not_changed_func(self.value, other.value)

    @classmethod
    def align_for_interpolate(cls, cmpt1: Cmpt_Data, cmpt2: Cmpt_Data) -> AlignedData[Self]:
        cmpt1_copy = cmpt1.copy()
        cmpt2_copy = cmpt2.copy()
        return AlignedData(cmpt1_copy, cmpt2_copy, cmpt1_copy.copy())

    def interpolate(self, cmpt1: Cmpt_Data, cmpt2: Cmpt_Data, alpha: float, *, path_func=None) -> None:
        if not self.not_changed_func(cmpt1, cmpt2) or not self.not_changed_func(cmpt1, self):
            if self.not_changed_func(cmpt1, cmpt2):
                self.set(cmpt1.copy_func(cmpt1.value))
            else:
                self.set(self.interpolate_func(cmpt1.value, cmpt2.value, alpha))

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
        not_changed_func: NotChangedFn[T] | None = None,
        interpolate_func: InterpolateFn[T] | None = None
    ) -> Self:
        if copy_func is not None:
            self.copy_func = copy_func
        if not_changed_func is not None:
            self.not_changed_func = not_changed_func
        if interpolate_func is not None:
            self.interpolate_func = interpolate_func
        return self
