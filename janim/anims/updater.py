from __future__ import annotations

import inspect
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Callable, Self

from janim.anims.animation import Animation, RenderCall, TimeRange
from janim.constants import ANIM_END_DELTA, C_LABEL_ANIM_ABSTRACT
from janim.exception import UpdaterError
from janim.items.item import DynamicItem, Item
from janim.utils.simple_functions import clip
from janim.locale.i18n import get_local_strings

_ = get_local_strings('updater')


@dataclass
class UpdaterParams:
    '''
    ``Updater`` 调用时会传递的参数，用于标注时间信息以及动画进度
    '''
    updater: DataUpdater | GroupUpdater | ItemUpdater
    global_t: float
    alpha: float
    range: TimeRange
    extra_data: tuple | None

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

    另见：:class:`~.UpdaterExample`
    '''
    label_color = C_LABEL_ANIM_ABSTRACT

    @dataclass
    class DataGroup:
        orig_data: Item
        data: Item
        extra_data: Any | None
        alpha_on: float | None = None

    def __init__(
        self,
        item: T,
        func: DataUpdaterFn[T],
        *,
        lag_ratio: float = 0,
        hide_at_begin: bool = True,
        show_at_end: bool = True,
        become_at_end: bool = True,
        skip_null_items: bool = True,
        root_only: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.item = item
        self.func = func
        self.lag_ratio = lag_ratio
        self.hide_at_begin = hide_at_begin
        self.show_at_end = show_at_end
        self.become_at_end = become_at_end
        self.skip_null_items = skip_null_items
        self.root_only = root_only

        self.post_updaters: list[DataUpdaterFn[T]] = []

        for subitem in item.walk_self_and_descendants(root_only):
            self.timeline.track(subitem)

    def add_post_updater(self, updater: DataUpdaterFn[T]) -> Self:
        self.post_updaters.append(updater)
        return self

    def call(self, data: T, p: UpdaterParams) -> None:
        self.func(data, p)
        for updater in self.post_updaters:
            updater(data, p)

    def create_extra_data(self, data: Item) -> Any | None:
        return None

    def wrap_dynamic(self, updater_data: DataUpdater.DataGroup) -> DynamicItem:
        '''
        以供传入 :meth:`~.Timeline.register_dynamic` 使用
        '''
        def wrapper(global_t: float) -> Item:
            alpha = self.get_alpha_on_global_t(global_t)
            if updater_data.alpha_on == alpha:
                return updater_data.data.store()

            data_copy = updater_data.orig_data.store()

            with UpdaterParams(self,
                               global_t,
                               alpha,
                               self.global_range,
                               updater_data.extra_data) as params:
                self.call(data_copy, params)

            return data_copy

        return wrapper

    def anim_init(self) -> None:
        def build_data(data: Item) -> DataUpdater.DataGroup:
            return DataUpdater.DataGroup(data, data.store(), self.create_extra_data(data))

        self.datas: dict[Item, DataUpdater.DataGroup] = {
            item: build_data(
                item.current(as_time=self.global_range.at,
                             skip_dynamic=True)
            )
            for item in self.item.walk_self_and_descendants(self.root_only)
            if not self.skip_null_items or not item.is_null()
        }

        for item, updater_data in self.datas.items():
            if self.become_at_end:
                with UpdaterParams(self,
                                   self.global_range.end,
                                   1,
                                   self.global_range,
                                   updater_data.extra_data) as params:
                    self.call(item, params)

            self.timeline.register_dynamic(item,
                                           self.wrap_dynamic(updater_data),
                                           item.store() if self.become_at_end else None,
                                           self.global_range.at,
                                           self.global_range.end - ANIM_END_DELTA,
                                           not self.become_at_end)

        self.set_render_call_list([
            RenderCall(
                updater_data.data.depth,
                updater_data.data.render
            )
            for updater_data in self.datas.values()
        ])

        # 在动画开始时自动隐藏，在动画结束时自动显示
        # 可以将 ``hide_on_begin`` 和 ``show_on_end`` 置为 ``False`` 以禁用
        if self.hide_at_begin:
            self.timeline.schedule(self.global_range.at, self.item.hide, root_only=self.root_only)
        if self.show_at_end:
            self.timeline.schedule(self.global_range.end, self.item.show, root_only=self.root_only)

    def anim_on_alpha(self, alpha: float) -> None:
        global_t = self.global_t_ctx.get()
        for i, updater_data in enumerate(self.datas.values()):
            sub_alpha = self.get_sub_alpha(alpha, i)

            # 如果此时将要插值的 sub_alpha 与上次的相同，则跳过
            if sub_alpha == updater_data.alpha_on:
                continue

            updater_data.alpha_on = sub_alpha
            updater_data.data.restore(updater_data.orig_data)

            with UpdaterParams(self,
                               global_t,
                               sub_alpha,
                               self.global_range,
                               updater_data.extra_data) as params:
                self.call(updater_data.data, params)

    def get_sub_alpha(
        self,
        alpha: float,
        index: int
    ) -> float:
        '''依据 ``lag_ratio`` 得到特定子物件的 ``sub_alpha``'''
        # REFACTOR: make this more understanable
        lag_ratio = self.lag_ratio
        full_length = (len(self.datas) - 1) * lag_ratio + 1
        value = alpha * full_length
        lower = index * lag_ratio
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
        hide_at_begin: bool = True,
        show_at_end: bool = True,
        become_at_end: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.item = item
        self.func = func
        self.hide_at_begin = hide_at_begin
        self.show_at_end = show_at_end
        self.become_at_end = become_at_end

        self.post_updaters: list[GroupUpdaterFn[T]] = []

        for subitem in item.walk_self_and_descendants():
            self.timeline.track(subitem)

    def add_post_updater(self, updater: GroupUpdaterFn[T]) -> Self:
        self.post_updaters.append(updater)
        return self

    def call(self, data: T, p: UpdaterParams) -> None:
        self.func(data, p)
        for updater in self.post_updaters:
            updater(data, p)

    def wrap_dynamic(self, idx: int) -> DynamicItem:
        def wrapper(global_t: float) -> Item:
            alpha = self.get_alpha_on_global_t(global_t)

            if self.alpha_on == alpha:
                if idx == 0:
                    return self.item_copy.store()
                return self.item_copy.descendants()[idx - 1].store()

            item_copy = self.item_orig.copy()

            with UpdaterParams(self,
                               global_t,
                               alpha,
                               self.global_range,
                               None) as params:
                self.call(item_copy, params)

            if idx == 0:
                return item_copy
            return item_copy.descendants()[idx - 1]

        return wrapper

    def anim_init(self) -> None:
        self.item_orig = self.item.copy(as_time=self.global_range.at, skip_dynamic=True)

        self.item_copy = self.item_orig.copy()
        self.alpha_on: float | None = None

        if self.become_at_end:
            with UpdaterParams(self,
                               self.global_range.end,
                               1,
                               self.global_range,
                               None) as params:
                self.call(self.item, params)

        # 这里假定 self.item 的后代物件结构未发生改变
        for i, item in enumerate(self.item.walk_self_and_descendants()):
            self.timeline.register_dynamic(item,
                                           self.wrap_dynamic(i),
                                           item.store() if self.become_at_end else None,
                                           self.global_range.at,
                                           self.global_range.end - ANIM_END_DELTA,
                                           not self.become_at_end)

        self.set_render_call_list([
            RenderCall(
                subitem.depth,
                subitem.render
            )
            for subitem in self.item_copy.walk_self_and_descendants()
        ])

        # 在动画开始时自动隐藏，在动画结束时自动显示
        # 可以将 ``hide_on_begin`` 和 ``show_on_end`` 置为 ``False`` 以禁用
        if self.hide_at_begin:
            self.timeline.schedule(self.global_range.at, self.item.hide)
        if self.show_at_end:
            self.timeline.schedule(self.global_range.end, self.item.show)

    def anim_on_alpha(self, alpha: float) -> None:
        global_t = self.global_t_ctx.get()
        self.item_copy.become(self.item_orig)
        self.alpha_on = alpha

        with UpdaterParams(self,
                           global_t,
                           alpha,
                           self.global_range,
                           None) as params:
            self.call(self.item_copy, params)


# TODO: optimize
class ItemUpdater(Animation):
    '''
    以时间为参数显示物件

    也就是说，在 :class:`ItemUpdater` 执行时，对于每帧，都会执行 ``func``，并显示 ``func`` 返回的物件

    在默认情况下：

    - 传入的 ``item`` 会在动画的末尾被替换为动画最后一帧 ``func`` 所返回的物件，传入 ``become_at_end=False`` 以禁用
    - 传入的 ``item`` 会在动画开始时隐藏，在动画结束后显示，传入 ``hide_at_begin=False`` 和 ``show_at_end=False`` 以禁用
    - 若传入 ``item=None``，则以上两点都无效

    另见：:class:`~.UpdaterExample`
    '''
    label_color = C_LABEL_ANIM_ABSTRACT

    def __init__(
        self,
        item: Item | None,
        func: Callable[[UpdaterParams], Item],
        *,
        hide_at_begin: bool = True,
        show_at_end: bool = True,
        become_at_end: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.func = func
        self.item = item
        self.hide_at_begin = hide_at_begin
        self.show_at_end = show_at_end
        self.become_at_end = become_at_end

    def call(self, p: UpdaterParams) -> Item:
        ret = self.func(p)
        if not isinstance(ret, Item):
            raise UpdaterError(
                _('The function passed to ItemUpdater must return an item, but got {ret} instead, '
                  'defined in {file}:{lineno}')
                .format(ret=ret, file=inspect.getfile(self.func), lineno=inspect.getsourcelines(self.func)[1])
            )
        for item in ret.walk_self_and_descendants():
            item.is_temporary = True
        return ret

    def anim_init(self) -> None:
        if self.item is None:
            return

        # 在动画开始时自动隐藏，在动画结束时自动显示
        # 可以将 ``hide_on_begin`` 和 ``show_on_end`` 置为 ``False`` 以禁用
        if self.hide_at_begin:
            self.timeline.schedule(self.global_range.at, self.item.hide)
        if self.show_at_end:
            self.timeline.schedule(self.global_range.end, self.item.show)

        # 在动画结束后，自动使用动画最后一帧的物件替换原有的
        if self.become_at_end:
            self.timeline.schedule(self.global_range.end, self.scheduled_become)

    def scheduled_become(self) -> None:
        with UpdaterParams(self,
                           self.global_range.end,
                           1,
                           self.global_range,
                           None) as params:
            self.item.become(self.call(params))

    def anim_on_alpha(self, alpha: float) -> None:
        global_t = self.global_t_ctx.get()

        with UpdaterParams(self, global_t, alpha, self.global_range, None) as params:
            dynamic = self.call(params)

        self.set_render_call_list([
            RenderCall(
                sub.depth,
                sub.render
            )
            for sub in dynamic.walk_self_and_descendants()
        ])
