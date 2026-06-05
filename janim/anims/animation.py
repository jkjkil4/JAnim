from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, overload

from janim.anims_core.time import FOREVER, ForeverType, TimeAligner, TimeRange
from janim.constants import C_LABEL_ANIM_DEFAULT, DEFAULT_DURATION
from janim.exception import AnimationError
from janim.items.item import Item
from janim.locale import get_translator
from janim.utils.rate_functions import RateFunc, linear, smooth

if TYPE_CHECKING:
    from janim.anims.anim_stack import AnimStack
    from janim.anims.composition import AnimGroup

_ = get_translator('janim.anims.animation')


class Animation:
    """
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
    """

    label_color: tuple[float, float, float] = C_LABEL_ANIM_DEFAULT

    def __init__(
        self,
        *,
        at: float = 0,
        duration: float | ForeverType = DEFAULT_DURATION,
        rate_func: RateFunc = smooth,
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
            FOREVER if duration is FOREVER else at + duration,
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
        **kwargs,
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

    @dataclass(slots=True)
    class ApplyParams:
        global_t: float
        anims: list[ItemAnimation]
        index: int

    @overload
    def apply(self, data: Item, p: ApplyParams) -> None: ...
    @overload
    def apply(self, data: None, p: ApplyParams) -> Item: ...

    def apply(self, data, params):
        """
        将 ``global_t`` 时的动画效果作用到 ``data`` 上

        其中

        - 对于 :class:`~.Display` 而言，``data`` 是 ``None``，返回值是 :class:`~.Item` 对象
        - 而对于其它大多数的而言，``data`` 是前一个动画作用的结果，返回值是 ``None``
        """
        pass


class ApplyAligner(ItemAnimation):
    def __init__(self, item: Item, stacks: list[AnimStack], **kwargs):
        super().__init__(item, **kwargs)
        self.stacks = stacks

    def pre_apply(self, data: Item, p: ItemAnimation.ApplyParams) -> None:
        pass
