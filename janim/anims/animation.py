from __future__ import annotations

import math
from bisect import bisect_left
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Iterable, Self, overload

from janim.constants import C_LABEL_ANIM_DEFAULT, DEFAULT_DURATION, FOREVER
from janim.exception import AnimationError
from janim.items.item import Item
from janim.locale.i18n import get_local_strings
from janim.typing import ForeverType
from janim.utils.rate_functions import RateFunc, linear, smooth

if TYPE_CHECKING:
    from janim.anims.anim_stack import AnimStack
    from janim.anims.composition import AnimGroup

_ = get_local_strings('animation')

ALIGN_EPSILON = 1e-6


class Animation:
    '''
    动画基类

    - 创建一个从 ``at`` 持续至 ``at + duration`` 的动画
    - ``duration`` 可以是 ``FOREVER``
      （一般用于 :class:`~.Display`，
      以及特殊情况下的 :class:`DataUpdater` 等，
      但是 :class:`~.AnimGroup` 及其衍生类不能传入 ``FOREVER``）
    - 指定 ``rate_func`` 可以设定插值函数，默认为 :meth:`janim.utils.rate_funcs.smooth` 即平滑插值

    - 设置 ``name`` 可以将文字显示在预览界面的时间轴标签上，不影响渲染（如果不设置则默认为类名）

    .. warning::

        动画对象不能复用，例如这样会导致意外行为：

        .. code-block:: python

            class Test(Timeline):
                def construct(self):
                    a = Square()
                    b = Circle()
                    anim1 = Transform(a, b)
                    anim2 = Transform(b, a)
                    self.play(anim1)
                    self.play(anim2)
                    self.play(anim1)

        正确写法：

        .. code-block:: python

            class Test(Timeline):
                def construct(self):
                    a = Square()
                    b = Circle()
                    self.play(Transform(a, b))
                    self.play(Transform(b, a))
                    self.play(Transform(a, b))
    '''
    label_color: tuple[float, float, float] = C_LABEL_ANIM_DEFAULT

    def __init__(
        self,
        *,
        at: float = 0,
        duration: float | ForeverType = DEFAULT_DURATION,
        rate_func: RateFunc = smooth,
        name: str | None = None
    ):
        self.parent: AnimGroup | None = None
        self.name = name

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

        from janim.anims.timeline import Timeline
        self.timeline = Timeline.get_context()

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

    def finalize(self) -> None:
        self._align_time(self.timeline.time_aligner)
        self._time_fixed()

    def _align_time(self, aligner: TimeAligner) -> None:
        aligner.align(self)
        if self.t_range.at < 0:
            raise AnimationError(_('Animation start time cannot be negative'))

    def _time_fixed(self) -> None:
        '''
        由子类实现，用于确定该动画的行为，并可用于该对象内容的初始化
        '''
        pass

    def get_alpha_on_global_t(self, global_t: float) -> float:
        if self.t_range.end is FOREVER:
            return 0
        alpha = (global_t - self.t_range.at) / self.t_range.duration
        for func in self.rate_funcs:
            alpha = func(alpha)
        return alpha

    def transfer_params(self, other: Animation) -> None:
        self.t_range = other.t_range
        self.rate_func = other.rate_func
        self.rate_funcs = other.rate_funcs

    global_t_ctx: ContextVar[float] = ContextVar('Animation.global_t_ctx')

    def schedule_show_and_hide(self, item: Item, show_at_begin: bool, hide_at_end: bool) -> None:
        if show_at_begin:
            self.timeline.schedule(self.t_range.at, item.show, root_only=True)
        if hide_at_end:
            self.timeline.schedule(self.t_range.end, item.hide, root_only=True)


class ItemAnimation(Animation):
    auto_detect = True

    def __init__(
        self,
        item: Item,
        *,
        show_at_begin: bool = True,
        hide_at_end: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.item = item
        self.show_at_begin = show_at_begin
        self.hide_at_end = hide_at_end

        # 有些动画是被其它动画生成的，例如 MethodTransform -> _MethodTransform，DataUpdater -> _DataUpdater 等
        # 记录这个信息，用于 Timeline.debug 显示在时间轴上时，得知原始的动画是那个
        self._generate_by: Animation | None = None

        # 意即“覆盖先前的动画”
        # 把该值置为 True 表示该动画不依赖先前动画的效果，使得进行计算时可以直接从该动画开始而不用考虑更前面的动画效果
        # 例如，该值会被 Display 置为 True，因为 Display 不基于更前面的动画
        self._cover_previous_anims = False

        self.stack = self.timeline.item_appearances[self.item].stack
        if self.auto_detect and not self.stack.has_detected_change():
            self.stack.detect_change(self.item, 0)

    def _time_fixed(self) -> None:
        self.stack.append(self)
        self.schedule_show_and_hide(self.item, self.show_at_begin, self.hide_at_end)

    @dataclass
    class ApplyParams:
        global_t: float
        anims: list[ItemAnimation]
        index: int

    @overload
    def apply(self, data: Item, p: ApplyParams) -> None: ...
    @overload
    def apply(self, data: None, p: ApplyParams) -> Item: ...

    def apply(self, data, params):
        '''
        将 ``global_t`` 时的动画效果作用到 ``data`` 上

        其中

        - 对于 :class:`~.Display` 而言，``data`` 是 ``None``，返回值是 :class:`~.Item` 对象
        - 而对于其它大多数的而言，``data`` 是前一个动画作用的结果，返回值是 ``None``
        '''
        pass


class ApplyAligner(ItemAnimation):
    def __init__(self, item: Item, stacks: list[AnimStack], **kwargs):
        super().__init__(item, **kwargs)
        self.stacks = stacks

    def pre_apply(self, data: Item, p: ItemAnimation.ApplyParams) -> None:
        pass


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

        - 当 ``end`` 是 ``FOREVER`` 时，此时返回 ``at``

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


class TimeAligner:
    '''
    由于浮点数精度的问题，有可能出现比如原本设计上首尾相连的两个动画，却出现判定的错位

    该类用于将相近的浮点数归化到同一个值，使得 :class:`TimeRange` 区间严丝合缝
    '''
    def __init__(self):
        self.recorded_times = []

    def align(self, anim: Animation) -> None:
        '''
        归化 ``anim`` 的时间区段，
        即分别对 ``.t_range.at`` 和 ``.t_range.end`` 进行 :meth:`align_t` 的操作
        '''
        rg = anim.t_range
        rg.at = self.align_t(rg.at)
        if rg.end is not FOREVER:
            rg.end = self.align_t(rg.end)

    def align_t(self, t: float) -> float:
        '''
        对齐时间 `t`，确保相近的时间点归化到相同的值，返回归化后的时间值
        '''
        t = float(t)    # 避免 numpy 类型浮点数可能导致的问题（例如影响到 GUI 绘制时传给 Qt 的类型）
        # 因为在大多数情况下，最新传入的 t 总是出现在列表的最后，所以倒序查找
        for i, recorded_t in enumerate(reversed(self.recorded_times)):
            # 尝试归化到已有的值
            if abs(t - recorded_t) < ALIGN_EPSILON:
                return recorded_t
            # 尝试插入到中间位置
            if t > recorded_t:
                # len - 1 - i 是 recorded_t 的位置，所以这里用 len - i 表示插入到其后面
                idx = len(self.recorded_times) - i
                self.recorded_times.insert(idx, t)
                return t

        # 循环结束表明所有已记录的都比 t 大，所以将 t 插入到列表开头
        self.recorded_times.insert(0, t)
        return t

    def align_t_for_render(self, t: float) -> float:
        '''
        与 :meth:`align_t` 类似，但区别在于

        - 该方法使用二分查找而不是倒序查找
        - 该方法在查找后不记录 ``t`` 的值
        '''
        idx = bisect_left(self.recorded_times, t)
        if idx != len(self.recorded_times):
            recorded_t = self.recorded_times[idx]
            if abs(t - recorded_t) < ALIGN_EPSILON:
                return recorded_t
        if idx != 0:
            recorded_t = self.recorded_times[idx - 1]
            if abs(t - recorded_t) < ALIGN_EPSILON:
                return recorded_t
        return t


class TimeSegments[T]:
    def __init__(self, iterable: Iterable[T], key: Callable[[T], TimeRange | Iterable[TimeRange]], *, step: float = 4):
        self.step = step
        self.segments: list[list[T]] = []

        for val in iterable:
            ret = key(val)
            prev_right = None
            for t_range in [ret] if isinstance(ret, TimeRange) else ret:
                left = math.floor(t_range.at / step)
                right = math.ceil(t_range.end / step)
                if prev_right is not None and left < prev_right:
                    left = prev_right
                if len(self.segments) < right:
                    self.segments.extend([].copy() for _ in range(right - len(self.segments)))
                for i in range(left, right):
                    self.segments[i].append(val)
                prev_right = right

    def get(self, t: float) -> list[T]:
        idx = math.floor(t / self.step)
        return self.segments[idx] if idx < len(self.segments) else []
