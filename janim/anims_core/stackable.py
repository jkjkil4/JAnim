from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from janim.anims_core.animation import Animation
from janim.items.item import Item

if TYPE_CHECKING:
    from janim.anims_core.anim_stack import AnimStack


class StackableAnimation(Animation):
    """
    可被记录到 :class:`~.AnimStack` 中的动画的基类

    主要实现 :meth:`apply` 的堆栈调用过程
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 有些动画是被其它动画生成的，例如 MethodTransform -> _MethodTransform，DataUpdater -> _DataUpdater 等
        # 记录这个信息，用于 Timeline.debug 显示在时间轴上时，得知原始的动画是那个
        self._generate_by: Animation | None = None

    def apply(self, params: ApplyParams) -> None:
        """
        具体请参考 :class:`StackableAnimation` 以及 :class:`ApplyParams` 的介绍
        """
        pass


@dataclass(slots=True)
class ApplyParams:
    """
    传递给 :meth:`apply` 的单对象参数

    -   ``data`` 表示当前计算中的物件状态，需要交由 :meth:`apply` 内部进行设置

        它会从 ``None`` 开始，随着对 :meth:`apply` 函数的调用，而逐渐被应用各个动画效果

        -   一开始，``data`` 是 ``None``，并总是会被 :class:`~.Display` 设置初始值

            因为我们在 :class:`~.AnimStack` 中
            直接调用 :meth:`~.AnimStack.display` 记录了一个 :class:`Display` 对象，
            所以动画堆栈中的首个动画总是 :class:`~.Display`

        -   随后，``data`` 每次都会被保留给下一个动画的 :meth:`apply` 函数，
            从而随着动画堆栈应用效果，走完整个动画堆栈得出最终的显示状态

    -   对于 ``index`` 来说，它会从 ``0`` 开始，随着对 :meth:`apply` 函数的调用，而逐渐增加

        即表示当前调用的动画在 ``anims`` 中的下标

    另外：

    -   ``global_t`` 表示当前的全局时刻

    -   ``index`` 表示当前动画在动画堆栈中的下标

    -   ``anims`` 即为当前的完整动画堆栈
    """

    data: Item

    global_t: float

    index: int
    anims: list[StackableAnimation]


class ItemAnimation(StackableAnimation):
    """
    大多数针对物件的动画的基类

    该类相比 :class:`StackableAnimation` 的主要区别是：

    - 自动将 ``item`` 加入 :class:`~.AnimStack` 的追踪

    - 封装 ``show_at_begin`` 与 ``hide_at_end`` 参数，提供了相对直接的显示/隐藏时机的控制
    """  # TODO: 说明 JAnim 中由动画而导致的显示/隐藏的逻辑规律

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

        self.timeline.track(item)

    def _time_fixed(self) -> None:
        apprs = self.timeline.item_appearances
        apprs[self.item].stack.append(self)

        self.schedule_show_and_hide(self.item, self.show_at_begin, self.hide_at_end)


class ApplyAligner(ItemAnimation):
    """
    用于处理多个动画堆栈之间的联动

    主要用于 :class:`~.GroupUpdater`

    说明：

    普通的 :class:`StackableAnimation` 只是单个动画堆栈从头 ``apply`` 到尾

    但是比如对于 :class:`~.GroupUpdater` 而言，
    它需要同时等待多个物件的动画堆栈到达一个预期的“闸”，当所有都“触闸”后，
    这个 :class:`~.GroupUpdater` 才能开始执行，执行结束后“开闸”才让各个动画堆栈继续执行

    机制：

    当 :class:`~.AnimStack` 在计算时，发现一个 :class:`ApplyAligner` 动画，
    则会先调用其 :meth:`pre_apply` 方法，进行一些事先准备（比如对于 :class:`~.GroupUpdater` 而言，是将当前动画堆栈的计算状态同步到其内部的物件组上）

    调用完 :meth:`pre_apply` 方法后，:class:`~.AnimStack` 会使用 ``yield`` 暂时挂起当前动画堆栈的执行，
    并触发需要等待的物件（即构造参数所收集的 ``stacks``）的计算，
    在它们都“触闸”后，正式执行 :meth:`StackableAnimation.apply` 方法，从而达到目标

    注：对于同一组物件的 :class:`ApplyAligner` 需要传入同一个 ``stacks``，以保证 :meth:`identifier` 识别正确
    """  # TODO: 实现 GroupStepUpdater 后在这里加上它

    def __init__(self, item: Item, stacks: list[AnimStack], **kwargs):
        super().__init__(item, **kwargs)
        self.stacks = stacks

    @property
    def identifier(self) -> int:
        return id(self.stacks)

    def pre_apply(self, params: ApplyParams) -> None:
        pass
