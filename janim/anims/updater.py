from __future__ import annotations

import inspect
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Callable, Self

from janim.anims.animation import Animation, RenderCall, TimeRange
from janim.anims.timeline import ANIM_END_DELTA, DynamicData
from janim.exception import UpdaterError
from janim.items.item import Item
from janim.utils.simple_functions import clip


@dataclass
class UpdaterParams:
    '''
    ``Updater`` 调用时会传递的参数，用于标注时间信息以及动画进度
    '''
    updater: DataUpdater | ItemUpdater
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
                        lambda data, p: data.cmpt.points.rotate(p.alpha * 180 * DEGREES).shift(p.alpha * 6 * RIGHT)
                    )
                )


    会产生一个“矩形从左侧旋转着移动到右侧”的动画

    注：使用 ``data.cmpt`` 即可访问物件的组件，例如物件的组件方法 ``item.points.xxx`` 对于数据来说则是通过 ``data.cmpt.points.xxx`` 来调用

    另见：:class:`~.UpdaterExample`
    '''
    label_color = (49, 155, 191)

    @dataclass
    class DataGroup:
        orig_data: Item.Data[Item]
        data: Item.Data[Item]
        extra_data: Any | None

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

    def create_extra_data(self, data: Item.Data) -> Any | None:
        return None

    def wrap_data(self, updater_data: DataUpdater.DataGroup) -> DynamicData:
        '''
        以供传入 :meth:`~.Timeline.register_dynamic_data` 使用
        '''
        def wrapper(global_t: float) -> Item.Data:
            alpha = self.get_alpha_on_global_t(global_t)
            data_copy = updater_data.orig_data._copy(updater_data.orig_data)

            with UpdaterParams(self,
                               global_t,
                               alpha,
                               self.global_range,
                               updater_data.extra_data) as params:
                self.func(data_copy, params)

            return data_copy
        return wrapper

    def anim_init(self) -> None:
        def build_data(data: Item.Data) -> DataUpdater.DataGroup:
            return DataUpdater.DataGroup(data, data._copy(data), self.create_extra_data(data))

        self.datas: dict[Item, DataUpdater.DataGroup] = {
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
                with UpdaterParams(self,
                                   self.global_range.end,
                                   1,
                                   self.global_range,
                                   updater_data.extra_data) as params:
                    self.func(item.ref_data(), params)
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

            with UpdaterParams(self,
                               global_t,
                               sub_alpha,
                               self.global_range,
                               updater_data.extra_data) as params:
                self.func(updater_data.data, params)

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
    '''
    以时间为参数显示物件

    也就是说，在 :class:`ItemUpdater` 执行时，对于每帧，都会执行 ``func``，并显示 ``func`` 返回的物件

    在默认情况下：

    - 传入的 ``item`` 会在动画的末尾被替换为动画最后一帧 ``func`` 所返回的物件，传入 ``become_at_end=False`` 以禁用
    - 传入的 ``item`` 会在动画开始时隐藏，在动画结束后显示，传入 ``hide_at_begin=False`` 和 ``show_at_end=False`` 以禁用
    - 若传入 ``item=None``，则以上两点都无效

    另见：:class:`~.UpdaterExample`
    '''
    label_color = DataUpdater.label_color

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
            raise UpdaterError(f'传入 ItemUpdater 的函数必须以一个物件作为返回值，而返回的是 {ret}，'
                               f'函数定义于 {inspect.getfile(self.func)}:{inspect.getsourcelines(self.func)[1]}')
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
                sub.ref_data().render
            )
            for sub in dynamic.walk_self_and_descendants()
        ])
