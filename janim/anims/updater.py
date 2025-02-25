from __future__ import annotations

import itertools as it
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Callable, Self

from janim.anims.anim_stack import AnimStack
from janim.anims.animation import Animation, ItemAnimation, TimeRange
from janim.constants import C_LABEL_ANIM_ABSTRACT
from janim.items.item import Item
from janim.locale.i18n import get_local_strings
from janim.utils.simple_functions import clip

_ = get_local_strings('updater')


@dataclass
class UpdaterParams:
    '''
    ``Updater`` 调用时会传递的参数，用于标注时间信息以及动画进度
    '''
    global_t: float
    alpha: float
    range: TimeRange
    extra_data: Any | None

    def __enter__(self) -> Self:
        self.token = updater_params_ctx.set(self)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        updater_params_ctx.reset(self.token)


updater_params_ctx: ContextVar[UpdaterParams] = ContextVar('updater_params_ctx')

type DataUpdaterFn[T] = Callable[[T, UpdaterParams], Any]
type GroupUpdaterFn[T] = Callable[[T, UpdaterParams], Any]


class DataUpdater[T: Item](Animation):
    '''
    以时间为参数对物件的数据进行修改

    例如：

    .. code-block:: python

        class Example(Timeline):
            def construct(self) -> None:
                rect = Rect()
                rect.points.to_border(LEFT)

                self.play(
                    DataUpdater(
                        rect,
                        lambda data, p: data.points.rotate(p.alpha * 180 * DEGREES).shift(p.alpha * 6 * RIGHT)
                    )
                )

    会产生一个“矩形从左侧旋转着移动到右侧”的动画

    并且，可以对同一个物件作用多个 updater，各个 updater 会依次调用

    注意：默认 ``root_only=True`` 即只对根物件应用该 updater；需要设置 ``root_only=False`` 才会对所有后代物件也应用该 updater

    另见：:class:`~.UpdaterExample`
    '''
    label_color = C_LABEL_ANIM_ABSTRACT

    def __init__(
        self,
        item: T,
        func: DataUpdaterFn[T],
        *,
        extra: Callable[[Item], Any | None] = lambda x: None,
        lag_ratio: float = 0,
        show_at_begin: bool = True,
        become_at_end: bool = True,
        skip_null_items: bool = True,
        root_only: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.item = item
        self.func = func
        self.extra = extra
        self.lag_ratio = lag_ratio
        self.show_at_begin = show_at_begin
        self.become_at_end = become_at_end
        self.skip_null_items = skip_null_items
        self.root_only = root_only

    def _time_fixed(self):
        from janim.anims.timeline import Timeline
        self.timeline = Timeline.get_context()

        items = [
            item
            for item in self.item.walk_self_and_descendants(self.root_only)
            if not self.skip_null_items or not item.is_null()
        ]
        count = len(items)

        for i, item in enumerate(items):
            stack = self.timeline.item_appearances[item].stack

            sub_updater = _DataUpdater(item,
                                       self.func,
                                       self.extra(item),
                                       self.lag_ratio,
                                       i,
                                       count,
                                       show_at_begin=self.show_at_begin)
            sub_updater.transfer_params(self)
            sub_updater.finalize(self.timeline.time_aligner)

            if self.become_at_end:
                anims = stack.get_at_left(self.t_range.end)
                item.restore(stack.compute_anims(self.t_range.end, anims))
                stack.detect_change(item, self.t_range.end)


class _DataUpdater(ItemAnimation):
    def __init__(
        self,
        item: Item,
        func: DataUpdaterFn,
        extra_data: Any | None,
        lag_ratio: float,
        index: int,
        count: int,
        *,
        show_at_begin: bool
    ):
        super().__init__(item, show_at_begin=show_at_begin)
        self.func = func
        self.extra_data = extra_data
        self.lag_ratio = lag_ratio
        self.index = index
        self.count = count

    def apply(self, data: Item, p: ItemAnimation.ApplyParams) -> None:
        with UpdaterParams(p.global_t,
                           self.get_sub_alpha(self.get_alpha_on_global_t(p.global_t)),
                           self.t_range,
                           self.extra_data) as params:
            self.func(data, params)

    def get_sub_alpha(self, alpha: float) -> float:
        '''依据 ``lag_ratio`` 得到特定子物件的 ``sub_alpha``'''
        lag_ratio = self.lag_ratio
        full_length = (self.count - 1) * lag_ratio + 1
        value = alpha * full_length
        lower = self.index * lag_ratio
        return clip((value - lower), 0, 1)


class GroupUpdater[T: Item](Animation):
    '''
    以时间为参数对一组物件的数据进行修改
    '''
    label_color = C_LABEL_ANIM_ABSTRACT

    def __init__(
        self,
        item: T,
        func: GroupUpdaterFn[T],
        *,
        show_at_begin: bool = True,
        become_at_end: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.item = item
        self.func = func
        self.show_at_begin = show_at_begin
        self.become_at_end = become_at_end

    @dataclass
    class DataGroup:
        data: Item
        stack: AnimStack
        updater: _GroupUpdater

    def _time_fixed(self):
        from janim.anims.timeline import Timeline
        timeline = Timeline.get_context()

        updaters = [
            _GroupUpdater(self, item, show_at_begin=self.show_at_begin)
            for item in self.item.walk_self_and_descendants()
        ]

        stacks = [timeline.item_appearances[item].stack for item in self.item.walk_self_and_descendants()]

        if self.become_at_end:
            for item, stack in zip(self.item.walk_self_and_descendants(), stacks):
                anims = stack.get_at_left(self.t_range.end)
                item.restore(stack.compute_anims(self.t_range.end, anims))

            with UpdaterParams(self.t_range.end, 1, self.t_range, None) as params:
                self.func(self.item, params)

            for item, stack in zip(self.item.walk_self_and_descendants(), stacks):
                stack.detect_change(item, self.t_range.end)

        self.data = self.item.copy()

        for sub_updater in updaters:
            sub_updater.transfer_params(self)
            sub_updater.finalize(timeline.time_aligner)

        self.data_groups = {
            item: GroupUpdater.DataGroup(data, stack, updater)
            for item, data, stack, updater in zip(self.item.walk_self_and_descendants(),
                                                  self.data.walk_self_and_descendants(),
                                                  stacks,
                                                  updaters)
        }

        if len(self.data_groups) == 1:
            group, = self.data_groups.values()
            group.updater.this = group
            group.updater.next = group
        else:
            first_group: GroupUpdater.DataGroup | None = None
            for g1, g2 in it.pairwise(self.data_groups.values()):
                g1.updater.this = g1
                g1.updater.next = g2
                if first_group is None:
                    first_group = g1
                last_group = g2
            last_group.updater.this = last_group
            last_group.updater.next = first_group


class _GroupUpdater(ItemAnimation):
    def __init__(
        self,
        orig_updater: GroupUpdater,
        item: Item,
        *,
        show_at_begin: bool
    ):
        super().__init__(item, show_at_begin=show_at_begin)
        self.orig_updater = orig_updater
        self.this: GroupUpdater.DataGroup | None = None
        self.next: GroupUpdater.DataGroup | None = None
        self.time: float | None = None

    def apply(self, data: Item, p: ItemAnimation.ApplyParams) -> None:
        assert self.this is not None
        assert self.next is not None

        self.time = p.global_t
        self.this.data.restore(data)

        # 原理是，当调用 apply 时，会递归使用 stack.compute 使得每个 _GroupUpdater 都进入 apply 函数
        # 到最后一个 _GroupUpdater，因为 self.next 是循环指向的，所以进入 else 分支
        # 因为此时所有 _GroupUpdater 都进入了 apply 函数，所以就可以调用 GroupUpdater 的 func 进行整体更新了
        if self.next.updater.time != p.global_t:
            self.next.stack.compute(p.global_t, True)
        else:
            with UpdaterParams(p.global_t,
                               self.get_alpha_on_global_t(p.global_t),
                               self.t_range,
                               None) as params:
                self.orig_updater.func(self.orig_updater.data, params)

        data.restore(self.this.data)
