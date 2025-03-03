from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from enum import IntFlag
from typing import Iterable, Self, overload

import numpy as np
import numpy.typing as npt

from janim.locale.i18n import get_local_strings

_ = get_local_strings('data')


class ContextSetter[T]:
    def __init__(self, ctx: ContextVar[T], val: T):
        self.ctx = ctx
        self.val = val

    def __enter__(self) -> Self:
        self.token = self.ctx.set(self.val)

    def __exit__(self, exc_type, exc_value, tb) -> None:
        self.ctx.reset(self.token)


class Array:
    '''
    使得在使用 ``.data = xxx`` 修改（赋值）后必定是不同的 id

    并且通过 ``.data`` 得到的 numpy 数组必定是只读的
    '''
    def __init__(self, *, dtype=np.float32):
        self._data = np.empty(0, dtype=dtype)

    def len(self) -> int:
        return len(self._data)

    @property
    def data(self) -> np.ndarray:
        return self._data

    @data.setter
    def data(self, data: npt.ArrayLike | Array) -> None:
        # 如果是设定的是 Array 对象，因为对方的内容肯定是 write=False，所以直接引用其内容
        if isinstance(data, Array):
            self._data = data._data
            return
        # 否则进行拷贝，这里的 np.array 对于 numpy 数组和其它 ArrayLike 数据
        # 都会在原数据之外产生拷贝，不会产生共用内存的情况
        self._data = np.array(data, dtype=self._data.dtype)
        self._data.setflags(write=False)

    def copy(self) -> Array:
        ret = Array(dtype=self._data.dtype)
        ret.data = self
        return ret

    def is_share(self, other: Array) -> bool:
        return self.data is other.data


@dataclass
class AlignedData[T]:
    '''
    数据对齐后的结构，用于 :meth:`~.Item.align_for_interpolate`
    '''
    data1: T
    data2: T
    union: T


class Margins:
    '''
    定义了一组四个边距：左、上、右、下，用于描述矩形周围边框的大小。

    如果直接传入单个数值，则表示为四个方向皆为该值
    '''
    @overload
    def __init__(self, buff: float | tuple[float], /): ...
    @overload
    def __init__(self, left: float, top: float, right: float, bottom: float, /): ...

    def __init__(self, left, top=None, right=None, bottom=None):
        if top is None and right is None and bottom is None:
            self.buff = left
        else:
            self.buff = (left, top, right, bottom)

        self.is_float = not isinstance(self.buff, Iterable)

    @property
    def left(self) -> float:
        return self.buff if self.is_float else self.buff[0]

    @property
    def top(self) -> float:
        return self.buff if self.is_float else self.buff[1]

    @property
    def right(self) -> float:
        return self.buff if self.is_float else self.buff[2]

    @property
    def bottom(self) -> float:
        return self.buff if self.is_float else self.buff[3]


MarginsType = Margins | float | tuple[float]


class Align(IntFlag):
    Center  = 0b0000_0000
    Left    = 0b0000_0001
    Right   = 0b0000_0100
    Top     = 0b0000_1000
    Bottom  = 0b0001_0000
