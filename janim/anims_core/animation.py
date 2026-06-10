from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING, Self

from janim.anims_core.time import FOREVER, ForeverType, TimeAligner, TimeRange
from janim.constants import C_LABEL_ANIM_DEFAULT, DEFAULT_DURATION
from janim.exception import AnimationError
from janim.items.item import Item
from janim.locale import get_translator
from janim.utils.rate_functions import RateFunc, linear, smooth

if TYPE_CHECKING:
    from janim.anims.composition import AnimGroup

_ = get_translator('janim.anims_core.animation')


class Animation:
    """
    动画基类

    定义了从 ``at`` 持续至 ``at + duration`` 的动画

    :param at: 动画的开始时间
    :param duration: 动画的持续时间；可以是 ``FOREVER``，比如创建持续生效的 Updater
    :param rate_func: 设定插值函数，默认为 :meth:`~.rate_funcs.smooth`
    :param name: 更改在预览界面中时间轴标签上显示的名字，与画面渲染无关；若不设置则默认为类名

    .. warning::

        动画对象不能复用，例如这样会导致意外行为：

        .. code-block:: python

            anim1 = Transform(a, b)
            anim2 = Transform(b, a)
            self.play(anim1)
            self.play(anim2)
            self.play(anim1)

        正确写法：

        .. code-block:: python

            self.play(Transform(a, b))
            self.play(Transform(b, a))
            self.play(Transform(a, b))
    """

    # 在预览界面中，时间轴标签的显示颜色
    label_color: tuple[float, float, float] = C_LABEL_ANIM_DEFAULT

    def __init__(
        self,
        *,
        at: float = 0,
        duration: float | ForeverType = DEFAULT_DURATION,
        rate_func: RateFunc = smooth,
        #
        name: str | None = None,
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
            FOREVER if duration is FOREVER else at + duration,  # type: ignore
        )

        # 传给该动画对象的 rate_func
        self.rate_func = rate_func

        # 该动画及父动画的 rate_func 组成的列表
        self.rate_funcs = [] if rate_func is linear else [rate_func]

        from janim.timeline import Timeline

        self.timeline = Timeline.get_context()

    def __anim__(self) -> Animation:
        # 请参考 AnimGroup._get_anim_object 中的说明
        return self

    def shift_range(self, delta: float) -> Self:
        """
        以 ``delta`` 的变化量移动时间区段
        """
        self.t_range.shift(delta)
        return self

    def scale_range(self, k: float) -> Self:
        """
        以 ``k`` 的倍率缩放时间区段（相对于 ``t=0`` 进行缩放）
        """
        self.t_range.scale(k)
        return self

    def _attach_rate_func(self, rate_func: RateFunc) -> None:
        self.rate_funcs.insert(0, rate_func)

    def finalize(self) -> None:
        self._align_time(self.timeline.time_aligner)
        self._time_fixed()

    def _align_time(self, aligner: TimeAligner) -> None:
        aligner.align_anim_and_record(self)
        if self.t_range.at < 0:
            raise AnimationError(_('Animation start time cannot be negative'))

    def _time_fixed(self) -> None:
        """
        由子类实现，用于确定该动画的行为，并可用于该对象内容的初始化
        """
        pass

    def get_alpha_on_global_t(self, global_t: float) -> float:
        if self.t_range.end is FOREVER:
            return 0
        alpha = (global_t - self.t_range.at) / self.t_range.duration
        for func in self.rate_funcs:
            alpha = func(alpha)
        return alpha

    def transfer_params(self, other: Animation) -> None:
        """
        将 ``other`` 中的动画参数，包括 ``t_range`` 和 ``rate_func(s)``，
        同步到该动画对象上
        """
        self.t_range = other.t_range
        self.rate_func = other.rate_func
        self.rate_funcs = other.rate_funcs

    global_t_ctx: ContextVar[float] = ContextVar('Animation.global_t_ctx')

    def schedule_show_and_hide(self, item: Item, show_at_begin: bool, hide_at_end: bool) -> None:
        assert self.t_range.end is not FOREVER
        if show_at_begin:
            self.timeline.schedule(self.t_range.at, item.show, root_only=True)
        if hide_at_end:
            self.timeline.schedule(self.t_range.end, item.hide, root_only=True)  # type: ignore
