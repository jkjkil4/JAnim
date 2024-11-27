from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from janim.utils.rate_functions import RateFunc, smooth

if TYPE_CHECKING:   # pragma: no cover
    from janim.anims.composition import AnimGroup
    from janim.components.depth import Cmpt_Depth


@dataclass
class TimeRange:
    '''
    标识了从 ``at`` 开始，持续时间为 ``duration`` 的时间区段

    ``end`` 即 ``at + duration``
    '''
    at: float
    duration: float

    @property
    def end(self) -> float:
        return self.at + self.duration

    def copy(self) -> TimeRange:
        return TimeRange(self.at, self.duration)

    def __eq__(self, other: TimeRange) -> bool:
        return self.at == other.at and self.duration == other.duration


class Animation:
    '''
    动画基类

    - 创建一个从 ``at`` 持续至 ``at + duration`` 的动画
    - 指定 ``rate_func`` 可以设定插值函数，默认为 :meth:`janim.utils.rate_functions.smooth` 即平滑插值
    '''
    label_color: tuple[float, float, float] = (128, 132, 137)

    def __init__(
        self,
        *,
        at: float = 0,
        duration: float = 1.0,
        rate_func: RateFunc = smooth,
    ):
        from janim.anims.timeline import Timeline
        self.timeline = Timeline.get_context()
        self.parent: AnimGroup = None
        self.current_alpha = None

        self.local_range = TimeRange(at, duration)
        self.global_range = None
        self.rate_func = rate_func

        self.render_call_list: list[RenderCall] = []

    def compute_global_range(self, at: float, duration: float) -> None:
        '''
        计算 :class:`~.Timeline` 上的时间范围

        该方法是被 :meth:`~.AnimGroup.set_global_range` 调用以计算的
        '''
        self.global_range = TimeRange(at, duration)

    def set_render_call_list(self, lst: list[RenderCall]) -> None:
        '''
        设置绘制调用，具体参考 :class:`RenderCall`
        '''
        self.render_call_list = sorted(lst, key=lambda x: x.depth, reverse=True)

    def anim_pre_init(self) -> None: '''在 :meth:`~.Timeline.detect_changes_of_all` 执行之前调用的初始化方法'''

    def anim_init(self) -> None: '''在 :meth:`~.Timeline.detect_changes_of_all` 执行之后调用的初始化方法'''

    def anim_on(self, local_t: float) -> None:
        '''
        将 ``local_t`` 换算为 ``alpha`` 并调用 :meth:`anim_on_alpha`
        '''
        alpha = self.rate_func(local_t / self.local_range.duration)
        self.anim_on_alpha(alpha)

    def get_alpha_on_global_t(self, global_t: float) -> float:
        '''
        传入全局 ``global_t``，得到物件在该时刻应当处于哪个 ``alpha`` 的插值
        '''
        if self.parent is None:
            return self.rate_func((global_t - self.global_range.at) / self.global_range.duration)

        anim_t = self.parent.get_anim_t(self.parent.get_alpha_on_global_t(global_t), self)
        return self.rate_func(anim_t / self.local_range.duration)

    def is_visible(self, global_t: float) -> bool:
        # + 1e-3 是为了避免在两端的浮点误差
        return self.global_range.at <= global_t + 1e-3 < self.global_range.end

    global_t_ctx: ContextVar[float] = ContextVar('Animation.global_t_ctx')
    '''
    对该值进行设置，使得进行 :meth:`anim_on` 和 :meth:`render` 时不需要将 ``global_t`` 作为参数传递也能获取到
    '''

    def anim_on_alpha(self, alpha: float) -> None:
        '''
        动画在 ``alpha`` 处的行为
        '''
        pass


@dataclass
class RenderCall:
    '''
    绘制调用

    - ``depth``: 该绘制的深度
    - ``func``: 该绘制所调用的函数

    具体机制：

    - 在每个动画对象中，都会使用 :meth:`~.Animation.set_render_call_list` 来设置该动画进行绘制时所执行的函数
    - 在进行渲染（具体参考 :meth:`~.TimelineAnim.render_all` ）时，会按照深度进行排序，依次对 ``func`` 进行调用，深度越高的越先调用

    例：

    - 在 :class:`~.Display` 中，设置了单个 :class:`RenderCall` ，作用是绘制物件
    - 在 :class:`~.Transform` 中，对于每个插值物件都设置了 :class:`RenderCall`，绘制所有的插值物件
    '''
    depth: Cmpt_Depth
    func: Callable[[], None]
