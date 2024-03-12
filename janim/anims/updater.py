
from dataclasses import dataclass
from typing import Any, Callable

from janim.anims.animation import Animation, RenderCall, TimeRange
from janim.anims.timeline import ANIM_END_DELTA, DynamicData
from janim.items.item import Item
from janim.utils.simple_functions import clip


@dataclass
class UpdaterParams:
    global_t: float
    alpha: float
    range: TimeRange
    extra_data: tuple | None


@dataclass
class UpdaterData:
    orig_data: Item.Data[Item]
    data: Item.Data[Item]
    extra_data: tuple | None


class TimeBasedUpdater[T: Item](Animation):
    '''
    以时间为参数的物件变换动画
    '''  # TODO: 例子
    label_color = (49, 155, 191)

    def __init__(
        self,
        item: T,
        func: Callable[[Item.Data[T], UpdaterParams], Any],
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

    def create_extra_data(self, data: Item.Data) -> tuple | None:
        return None

    def wrap_data(self, updater_data: UpdaterData) -> DynamicData:
        '''
        以供传入 :meth:`~.Timeline.register_dynamic_data` 使用
        '''
        def wrapper(global_t: float) -> Item.Data:
            alpha = self.get_alpha_on_global_t(global_t)
            data_copy = updater_data.orig_data._copy(updater_data.orig_data)
            self.func(data_copy, UpdaterParams(global_t,
                                               alpha,
                                               self.global_range,
                                               updater_data.extra_data))
            return data_copy
        return wrapper

    def anim_init(self) -> None:
        def build_data(data: Item.Data) -> UpdaterData:
            return UpdaterData(data, data._copy(data), self.create_extra_data(data))

        self.datas: dict[Item, UpdaterData] = {
            item: build_data(
                self.timeline.get_stored_data_at_right(
                    item,
                    self.global_range.at,
                    skip_dynamic_data=True
                )
            )
            for item in (
                [self.item]
                if self.root_only
                else self.item.walk_self_and_descendants()
            )
            if not self.skip_null_items or not item.is_null()
        }

        for item, updater_data in self.datas.items():
            if self.become_at_end:
                self.func(item.ref_data(), UpdaterParams(self.global_range.end,
                                                         1,
                                                         self.global_range,
                                                         updater_data.extra_data))
            self.timeline.register_dynamic_data(item, self.wrap_data(updater_data), self.global_range.at)

        self.timeline.detect_changes([self.item] if self.root_only else self.item.walk_self_and_descendants(),
                                     as_time=self.global_range.end - ANIM_END_DELTA)

        self.set_render_call_list([
            RenderCall(
                updater_data.data.cmpt.depth,
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
            updater_data.data._restore(updater_data.orig_data)
            self.func(
                updater_data.data,
                UpdaterParams(global_t,
                              sub_alpha,
                              self.global_range,
                              updater_data.extra_data)
            )

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


class ItemUpdater(Animation):
    # TODO: 注释
    label_color = TimeBasedUpdater.label_color

    def __init__(
        self,
        func: Callable[[UpdaterParams], Item],
        item: Item = None,
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
            self.timeline.schedule(
                self.global_range.end,
                lambda: self.item.become(self.func(UpdaterParams(self.global_range.end,
                                                                 1,
                                                                 self.global_range,
                                                                 None)))
            )

    def anim_on_alpha(self, alpha: float) -> None:
        global_t = self.global_t_ctx.get()
        dynamic = self.func(UpdaterParams(global_t, alpha, self.global_range, None))
        self.set_render_call_list([
            RenderCall(
                sub.depth,
                sub.ref_data().render
            )
            for sub in dynamic.walk_self_and_descendants()
        ])
