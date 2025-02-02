from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from janim.constants import FOREVER
from janim.typing import ForeverType
from janim.utils.rate_functions import RateFunc, linear, smooth


@dataclass
class TimeRange:
    '''
    标识了从 ``at`` 开始，到 ``end`` 结束的时间区段

    ``end`` 也可以是 ``FOREVER``
    '''

    at: float
    '''时间区段的开始时刻'''

    end: float | ForeverType
    '''时间区段的结束时刻'''

    @property
    def duration(self) -> float:
        '''
        时间区段的时长，即 ``end - at``，如果 ``end=FOREVER`` 则抛出 ``AssertionError``

        另见 :meth:`num_duration`
        '''
        assert self.end is not FOREVER
        return self.end - self.at

    @property
    def num_duration(self) -> float:
        '''
        - 当 ``end`` 不是 ``FOREVER`` 时，与 :meth:`duration` 一致

        - 当 ``end`` 是 ``FOREVER`` 时，此时返回 ``0``

        （这用于 :class:`~.AnimGroup` 对 ``end=FOREVER`` 的子动画的处理，也就是把这种子动画当成 ``end=at`` 来计算时间）
        '''
        return 0 if self.end is FOREVER else self.duration

    @property
    def num_end(self) -> float:
        '''
        - 当 ``end`` 不是 ``FOREVER`` 时，此时返回 ``end``

        - 当 ``end`` 是 ``FOREVER`` 时，此时返回 ``0``

        （这用于 :class:`~.AnimGroup` 对 ``end=FOREVER`` 的子动画的处理，也就是把这种子动画当成 ``end=at`` 来计算时间）
        '''
        return self.at if self.end is FOREVER else self.end

    def set(self, at: float, end: float | ForeverType) -> None:
        '''
        设置该时间区段的范围
        '''
        self.at = at
        self.end = end

    def shift(self, delta: float) -> None:
        '''
        以 ``delta`` 的变化量移动时间区段
        '''
        self.at += delta
        if self.end is not FOREVER:
            self.end += delta

    def scale(self, k: float) -> None:
        '''
        以 ``k`` 的倍率缩放时间区段（相对于 ``t=0`` 进行缩放）
        '''
        self.at *= k
        if self.end is not FOREVER:
            self.end *= k

    def copy(self) -> TimeRange:
        return TimeRange(self.at, self.end)

    def __eq__(self, other: TimeRange) -> bool:
        return self.at == other.at and self.end == other.end


class Animation:
    '''
    动画基类

    - 创建一个从 ``at`` 持续至 ``at + duration`` 的动画
    - ``duration`` 可以是 ``FOREVER``
      （一般用于 :class:`DirectModifier`，
      以及特殊情况下的 :class:`DataModifier` 等，
      但是 :class:`~.AnimGroup` 及其衍生类不能传入 ``FOREVER``）
    - 指定 ``rate_func`` 可以设定插值函数，默认为 :meth:`janim.utils.rate_funcs.smooth` 即平滑插值
    '''
    # TODO: label_color

    def __init__(
        self,
        *,
        at: float = 0,
        duration: float | ForeverType = 1.0,
        rate_func: RateFunc = smooth
    ):
        # 用于在 AnimGroup 中标记子动画是否都对齐；
        # 对于单个动画来说肯定是对齐的，默认为 True，而在 AnimGroup 中有可能是 False
        # 关于 is_aligned 的计算请参见 AnimGroup.__init__ 代码内的注释
        self.is_aligned = True

        # 用于标记该动画的全局时间区段
        self.t_range = TimeRange(
            at,
            FOREVER if duration is FOREVER else at + duration
        )

        # 传给该动画对象的 rate_func
        self.rate_func = rate_func

        # 该动画及父动画的 rate_func 组成的列表
        self.rate_funcs = [] if rate_func is linear else [rate_func]

    def __anim__(self) -> Self:
        return self

    def shift_range(self, delta: float) -> Self:
        '''
        以 ``delta`` 的变化量移动时间区段
        '''
        self.t_range.shift(delta)

    def scale_range(self, k: float) -> Self:
        '''
        以 ``k`` 的倍率缩放时间区段（相对于 ``t=0`` 进行缩放）
        '''
        self.t_range.scale(k)

    def _attach_rate_func(self, rate_func: RateFunc) -> None:
        self.rate_funcs.insert(0, rate_func)

    def _time_fixed(self) -> None:
        '''
        由子类实现，用于确定该动画的行为，并可用于该对象内容的初始化
        '''
        pass

    # TODO: anim_on

    # TODO: get_alpha_on_global_t

    # TODO: is_visible

    # TODO: global_t_ctx

    # TODO: anim_on_alpha
