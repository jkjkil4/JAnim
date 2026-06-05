from __future__ import annotations

from bisect import bisect_left
import math
import types
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Iterable, Self

if TYPE_CHECKING:
    from janim.anims.animation import Animation

__all__ = [
    'ForeverType',
    'FOREVER',
    'TimeRange',
    'TimeAligner',
    'TimeChunks',
]

type ForeverType = types.EllipsisType

FOREVER = ...
_ALIGN_EPSILON = 1e-6


@dataclass(slots=True)
class TimeRange:
    """
    标识了从 ``at`` 开始，到 ``end`` 结束的时间区段

    若 ``end`` 为 ``FOREVER``，则表示该时长是无限的
    """

    at: float
    """
    时间区段的开始时刻
    """

    end: float | ForeverType
    """
    时间区段的结束时刻

    若为 ``FOREVER``，则表示该时长是无限的
    """

    @property
    def duration(self) -> float:
        """
        时间区段的时长

        如果 ``end=FOREVER`` 则抛出 ``AssertionError``
        """
        assert self.end is not FOREVER
        return self.end - self.at  # type: ignore

    @property
    def num_duration(self) -> float:
        """
        - 当 ``end`` 不是 ``FOREVER`` 时，与 ``duration`` 一致
        - 当 ``end`` 是 ``FOREVER`` 时，此时返回 ``0``
        """
        return 0 if self.end is FOREVER else self.duration  # type: ignore

    @property
    def num_end(self) -> float:
        """
        - 当 ``end`` 不是 ``FOREVER`` 时，与 ``end`` 一致
        - 当 ``end`` 是 ``FOREVER`` 时，此时返回 ``at``
        """
        return self.at if self.end is FOREVER else self.end  # type: ignore

    def set(self, at: float, end: float | ForeverType) -> None:
        """
        设置该时间区段的范围
        """
        self.at = at
        self.end = end

    def shift(self, delta: float) -> None:
        """
        以 ``delta`` 的变化量移动时间区段
        """
        self.at += delta
        if self.end is not FOREVER:
            self.end += delta  # type: ignore

    def scale(self, k: float) -> None:
        """
        以 ``k`` 的倍率缩放时间区段（相对于 ``t=0`` 进行缩放）
        """
        self.at *= k
        if self.end is not FOREVER:
            self.end *= k  # type: ignore

    def copy(self) -> Self:
        """
        复制一份该对象
        """
        return self.__class__(self.at, self.end)

    def __eq__(self, other: Self) -> bool:  # type: ignore
        return self.at == other.at and self.end == other.end

    def contains(self, t: float) -> bool:
        """
        检查 ``t`` 是否位于该时间区段的内部
        """
        if self.end is FOREVER:
            return self.at <= t
        else:
            return self.at <= t < self.end  # type: ignore


class TimeAligner:
    """
    由于浮点数精度的问题，有可能出现比如原本设计上首尾相连的两个动画，却出现判定的错位

    该类用于将相近的浮点数归化到同一个值，使得 :class:`TimeRange` 区间严丝合缝
    """

    def __init__(self):
        self._recorded_times = []

    def align_anim_and_record(self, anim: Animation) -> None:
        """
        归化 ``anim`` 的时间区段，并参与记录

        即分别对其 ``.t_range.at`` 和 ``.t_range.end`` 进行 :meth:`align_and_record` 的操作
        """
        t_range = anim.t_range
        t_range.at = self.align_and_record(t_range.at)
        if t_range.end is not FOREVER:
            t_range.end = self.align_and_record(t_range.end)  # type: ignore

    def align_and_record(self, t: float) -> float:
        """
        对齐时间 ``t``，若没有极近的时间点，则记录

        确保极近的时间点归化到相同的值，返回归化后的时间值
        """
        t = float(t)  # 避免 numpy 类型浮点数可能导致的问题（例如影响到 GUI 绘制时传给 Qt 的类型）

        idx = bisect_left(self._recorded_times, t)

        # 尝试归化到右侧已有值
        if idx != len(self._recorded_times):
            recorded_t = self._recorded_times[idx]
            if recorded_t - t < _ALIGN_EPSILON:
                return recorded_t

        # 尝试归化到左侧已有值
        if idx != 0:
            recorded_t = self._recorded_times[idx - 1]
            if t - recorded_t < _ALIGN_EPSILON:
                return recorded_t

        # 没有可归化的值时则插入到列表中
        self._recorded_times.insert(idx, t)
        return t

    def align(self, t: float) -> float:
        """
        尝试对齐时间 ``t`` 到极近的时间点，不参与记录
        """
        idx = bisect_left(self._recorded_times, t)
        if idx != len(self._recorded_times):
            recorded_t = self._recorded_times[idx]
            if recorded_t - t < _ALIGN_EPSILON:
                return recorded_t
        if idx != 0:
            recorded_t = self._recorded_times[idx - 1]
            if t - recorded_t < _ALIGN_EPSILON:
                return recorded_t
        return t


class TimeChunks[T]:
    """
    用于优化对带有 :class:`TimeRange` 信息的对象，基于特定时刻的检索

    动机是：

    我们在时间轴上可能会有一系列的对象，这些对象的“可视时间”是零散分布的，
    我们并不希望在检索 “某个 ``t`` 时刻可视的有哪些” 时遍历整个列表结构

    但是由于这些可视时间是由区间表示的，所以不方便使用二分的方法来优化

    该类的目的是，划分出各个区块，每个区块的时长为 ``step``，记录在各个区块中有哪些是可见的，
    在检索 ``t`` 时刻可视物件时，调用侧使用 :meth:`get` 方法，即可得到 ``t`` 时刻所在区块中的所有对象，
    后续只需遍历这个区块内的对象检查是否可视即可

    :param iterable:
        一系列的对象

    :param key:
        将每个对象对应到其 :class:`TimeRange` 的函数

        可以返回单个 :class:`TimeRange`，也可以返回一个 :class:`TimeRange` 列表表示多个可视的区段

    :param step:
        每个区块的时长
    """

    def __init__(
        self,
        iterable: Iterable[T],
        key: Callable[[T], TimeRange | Iterable[TimeRange]],
        *,
        step: float = 4,
    ):
        self._step = step
        self._chunks: list[list[T]] = []

        for val in iterable:
            prev_right = None
            for t_range in self._get_ranges(val, key):
                # left, right 表示当前可视 t_range 范围所覆盖的区块范围，左闭右开
                left = math.floor(t_range.at / step)
                right = math.ceil(t_range.end / step)  # type: ignore
                # 限制 left 不能小于 prev_right，避免重复记录
                if prev_right is not None and left < prev_right:
                    left = prev_right

                if len(self._chunks) < right:
                    self._chunks.extend([].copy() for _ in range(right - len(self._chunks)))
                for i in range(left, right):
                    self._chunks[i].append(val)

                prev_right = right

    @staticmethod
    def _get_ranges(val: T, key: Callable[[T], TimeRange | Iterable[TimeRange]]):
        """
        提取 ``val`` 对象的各个时间范围
        """
        ret = key(val)
        if isinstance(ret, TimeRange):
            yield ret
        else:
            yield from ret

    def get(self, t: float) -> list[T]:
        """
        得到 ``t`` 时刻所在区块中的所有对象
        """
        idx = math.floor(t / self._step)
        return self._chunks[idx] if idx < len(self._chunks) else []
