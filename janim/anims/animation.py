from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from janim.components.depth import Cmpt_Depth
from janim.utils.rate_functions import RateFunc, smooth

if TYPE_CHECKING:
    from janim.anims.composition import AnimGroup


@dataclass
class TimeRange:
    at: float
    duration: float

    @property
    def end(self) -> float:
        return self.at + self.duration


@dataclass
class RenderCall:
    depth: Cmpt_Depth
    func: Callable[[], None]


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

    def set_global_range(self, at: float, duration: float | None = None) -> None:
        '''
        设置在 Timeline 上的时间范围

        不需要手动设置，该方法是被 :meth:`~.AnimGroup.set_global_range` 调用以计算的
        '''
        if duration is None:
            duration = self.local_range.duration
        self.global_range = TimeRange(at, duration)

    def set_render_call_list(self, lst: list[RenderCall]) -> None:
        self.render_call_list = sorted(lst, key=lambda x: x.depth, reverse=True)

    def anim_pre_init(self) -> None: '''在 :meth:`~.Timeline.detect_changes_of_all` 执行之前调用的初始化方法'''

    def anim_init(self) -> None: '''在 :meth:`~.Timeline.detect_changes_of_all` 执行之前调用的初始化方法'''

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

    global_t_ctx: ContextVar[float] = ContextVar('Animation.global_t_ctx')
    '''
    对该值进行设置，使得进行 :meth:`anim_on` 和 :meth:`render` 时不需要将 ``global_t`` 作为参数传递也能获取到
    '''

    def anim_on_alpha(self, alpha: float) -> None:
        '''
        动画在 ``alpha`` 处的行为
        '''
        pass
