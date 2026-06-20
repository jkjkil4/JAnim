from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from janim.anims_core.stackable import ApplyParams, StackableAnimation
from janim.anims_core.time import FOREVER
from janim.items.item import Item
from janim.utils.data import ContextSetter

type DisplayTypes = Display | DelayedDisplay


class Display(StackableAnimation):
    """
    用于标记物件在特定时间区段中的数据

    作为 :meth:`~.AnimStack.display` 的产物，表示“物件从一个特定时间开始，被更改为了这样的数据”

    另见：:meth:`~.Timeline.detect_changes_of_all`
    """

    def __init__(self, data: Item, **kwargs):
        super().__init__(**kwargs)
        self._be_covered: bool = False

        self.data = data
        self.data_orig = data.store()

    def apply(self, params: ApplyParams) -> None:
        """
        给 ``params`` 初始化物件数据

        将 ``self.data`` 重置为 ``self.data_orig`` 的数据并设置到 ``params.data`` 上，避免原始数据被意外更改

        特殊情况：

        当 :class:`~.AnimStack` 的动画堆栈只有一个动画，即该类型动画时，不会经由该方法，
        而是直接被其访问 ``data_orig``，起到一点点优化的作用
        """
        self.data.restore(self.data_orig)  # type: ignore
        params.data = self.data  # type: ignore


class DelayedDisplay(StackableAnimation):
    """
    和 :class:`Display` 基本一样，但是会在时间轴全局时刻到达 ``.t_range.at`` 后才调用 ``func`` 函数设置 ``data`` 状态

    :param item: 状态挂载给哪个物件
    :param func: 当全局时刻到达 ``.t_range.at`` 后的回调函数，需要返回一个 :class:`~.Item` 作为物件状态
    """

    def __init__(self, item: Item, func: Callable[[DelayedDisplayParams], Item], **kwargs):
        super().__init__(**kwargs)
        self._be_covered: bool = False  # 请另行参考 AnimStack.set_latest_display 中的注释

        self._item = item
        self._func = func
        self._stack = self.timeline.item_appearances[item].stack

    def apply(self, params: ApplyParams) -> None:
        self.data.restore(self.data_orig)  # type: ignore
        params.data = self.data  # type: ignore

    def _finalized(self) -> None:
        self._stack.set_latest_display(self)

        self.timeline.schedule(self.t_range.at, self._delayed_setup)
        self.add_to_stack(self._item, _is_display=True)

    def _delayed_setup(self) -> None:
        is_latest_display = not self._be_covered

        self.data = self._func(DelayedDisplayParams(is_latest_display))
        self.data_orig = self.data.store()
        if is_latest_display:
            self._stack._active_display = self


@dataclass(slots=True)
class DelayedDisplayParams:
    is_latest_display: bool


class DoBecomeAtEnd(DelayedDisplay):
    """
    对 :class:`DelayedDisplay` 针对各个动画 ``become_at_end`` 参数实现的封装

    即注册到 ``end~FOREVER`` 时段，将 ``end`` 时刻前计算出的动画状态作为显示状态；
    并在 ``is_latest_display=True`` 时自动 :meth:`~.Item.restore`
    """

    def __init__(self, item: Item, end: float, **kwargs):
        super().__init__(item, self._do_become_at_end, at=end, duration=FOREVER, **kwargs)

    def _do_become_at_end(self, params: DelayedDisplayParams) -> Item:
        from janim.anims_core.anim_stack import AnimStack

        stack = self._stack
        with ContextSetter(AnimStack.get_at_left_ctx, True):
            data = stack.compute(self.t_range.at, True)
        if params.is_latest_display:
            self._item.restore(data)
        return data
