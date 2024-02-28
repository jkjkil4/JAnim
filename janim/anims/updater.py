
from dataclasses import dataclass
from typing import Any, Callable

from janim.anims.animation import Animation, RenderCall
from janim.anims.timeline import ANIM_END_DELTA, DynamicData
from janim.items.item import Item


@dataclass
class UpdaterParams:
    global_t: int
    alpha: int


@dataclass
class UpdaterData:
    orig_data: Item.Data[Item]
    data: Item.Data[Item]


class TimeBasedUpdater[T: Item](Animation):
    label_color = (49, 155, 191)

    def __init__(
        self,
        item: T,
        func: Callable[[Item.Data[T], UpdaterParams], Any],
        *,
        hide_at_begin: bool = True,
        show_at_end: bool = True,
        become_at_end: bool = True,
        root_only: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.item = item
        self.func = func
        self.hide_at_begin = hide_at_begin
        self.show_at_end = show_at_end
        self.become_at_end = become_at_end
        self.root_only = root_only

    def wrap_data(self, updater_data: UpdaterData) -> DynamicData:
        '''
        以供传入 :meth:`~.Timeline.register_dynamic_data` 使用
        '''
        def wrapper(global_t: float) -> Item.Data:
            alpha = self.get_alpha_on_global_t(global_t)
            data_copy = updater_data.orig_data._copy(updater_data.orig_data)
            self.func(data_copy, UpdaterParams(global_t, alpha))
            return data_copy
        return wrapper

    def anim_init(self) -> None:
        def build_data(data: Item.Data) -> UpdaterData:
            return UpdaterData(data, data._copy(data))

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
        }

        end_params = UpdaterParams(self.global_range.end, 1)

        if self.become_at_end:
            self.func(self.item.ref_data(), end_params)
            if not self.root_only:
                for item in self.item.descendants():
                    self.func(item.ref_data(), end_params)

        for updater_data in self.datas.values():
            self.timeline.register_dynamic_data(self.item, self.wrap_data(updater_data), self.global_range.at)

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
        params = UpdaterParams(global_t, alpha)
        for updater_data in self.datas.values():
            updater_data.data._become(updater_data.orig_data)
            self.func(updater_data.data, params)
