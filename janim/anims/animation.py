from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

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


class Animation:
    '''
    动画基类

    - 创建一个从 ``at`` 持续至 ``at + duration`` 的动画
    - 指定 ``rate_func`` 可以设定插值函数，默认为 :meth:`janim.utils.rate_functions.smooth` 即平滑插值
    '''
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

    def set_global_range(self, at: float, duration: float | None = None) -> None:
        '''
        设置在 Timeline 上的时间范围

        不需要手动设置，该方法是被 :meth:`~.AnimGroup.set_global_range` 调用以计算的
        '''
        if duration is None:
            duration = self.local_range.duration
        self.global_range = TimeRange(at, duration)

    def anim_pre_init(self) -> None: ...

    def anim_init(self) -> None: ...

    def anim_on(self, local_t: float) -> None:
        '''
        将 ``local_t`` 换算为 ``alpha`` 并调用 :meth:`anim_on_alpha`
        '''
        alpha = self.rate_func(local_t / self.local_range.duration)
        self.anim_on_alpha(alpha)

    def get_alpha_on_global_t(self, global_t: float) -> float:
        if self.parent is None:
            return self.rate_func((global_t - self.global_range.at) / self.global_range.duration)

        anim_t = self.parent.get_anim_t(self.parent.get_alpha_on_global_t(global_t), self)
        return self.rate_func(anim_t / self.local_range.duration)

    global_t_ctx: ContextVar[float] = ContextVar('Animation.global_t_ctx')

    def anim_on_alpha(self, alpha: float) -> None:
        '''
        动画在 ``alpha`` 处的行为
        '''
        pass

    def render(self) -> None:
        pass
