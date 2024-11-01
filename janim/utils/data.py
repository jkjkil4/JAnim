from __future__ import annotations

from bisect import bisect_right
from contextvars import ContextVar
from dataclasses import dataclass
from enum import IntFlag
from typing import Iterable, Self, overload

import numpy as np
import numpy.typing as npt

from janim.constants import GET_DATA_DELTA
from janim.exception import RecordFailedError, RecordNotFoundError
from janim.logger import log
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


class History[T]:
    @dataclass
    class TimedData[DataT]:
        time: float
        data: DataT
        replaceable: bool

    def __init__(self):
        self.lst: list[History.TimedData[T]] = []

    def record_as_time(self, t: float, data: T, *, replaceable=False) -> T:
        '''
        标记在 ``t`` 时刻后，数据为 ``data``

        - ``t`` 必须比现有的所有时刻都大
        - 如果此时 没有已存储的记录，则将 ``t`` 视为 ``0``
        '''
        # 将 t 之后的 replaceable 数据都移除
        i = 0
        for i, timed_data in enumerate(reversed(self.lst)):
            if not timed_data.replaceable or t >= timed_data.time:
                break
        if i != 0:
            self.lst = self.lst[:-i]

        # 检查是否比最后一个迟，如果不是则抛出异常
        if self.lst and t < self.lst[-1].time:
            for timed_data in self.lst:
                log.debug(timed_data)
            log.debug(f'{t=}')
            raise RecordFailedError(_('Failed to record data, possibly because the item is in an animation state'))

        # 添加
        self.lst.append(History.TimedData(t if self.lst else 0,
                                          data,
                                          replaceable))

    def has_record(self) -> bool:
        return bool(self.lst)

    def latest(self) -> TimedData[T]:
        return self.lst[-1]

    def get_at_time(self, t: float) -> T:
        '''
        得到在指定时间的数据

        在两份数据的分界处请使用 :meth:`get_at_right` 和 :meth:`get_at_left` 来明确
        '''
        if not self.lst:
            raise RecordNotFoundError()

        index = bisect_right(self.lst, t, key=lambda x: x.time)
        index -= 1

        assert index >= 0
        return self.lst[index].data

    def get_at_right(self, t: float) -> T:
        '''
        得到在指定时间之后的瞬间的数据
        '''
        return self.get_at_time(t + GET_DATA_DELTA)

    def get_at_left(self, t: float) -> T:
        '''
        得到在指定时间之前的瞬间的数据
        '''
        return self.get_at_time(t - GET_DATA_DELTA)

    def get(self, t: float) -> T:
        '''
        :meth:`get_at_right` 的简写
        '''
        return self.get_at_right(t)


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
