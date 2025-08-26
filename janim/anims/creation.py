
import math
from dataclasses import dataclass
from typing import Callable

import numpy as np
from janim.anims.animation import Animation
from janim.anims.updater import DataUpdater, UpdaterParams
from janim.components.vpoints import Cmpt_VPoints
from janim.constants import (C_LABEL_ANIM_ABSTRACT, C_LABEL_ANIM_IN,
                             C_LABEL_ANIM_INDICATION, C_LABEL_ANIM_OUT,
                             NAN_POINT)
from janim.items.item import Item
from janim.items.points import Group
from janim.items.vitem import VItem
from janim.typing import JAnimColor
from janim.utils.bezier import integer_interpolate
from janim.utils.rate_functions import RateFunc, double_smooth, linear

DEFAULT_DRAWBORDER_THENFILL_STROKE_RADIUS = 0.01


class ShowPartial(DataUpdater):
    '''
    显示物件一部分的动画，显示的部分由 ``bound_func`` 决定
    '''
    label_color = C_LABEL_ANIM_ABSTRACT

    def __init__(
        self,
        item: Item,
        bound_func: Callable[[UpdaterParams], tuple[int, int]],
        *,
        auto_close_path: bool = False,
        become_at_end: bool = False,
        root_only: bool = False,
        zero_bound: int | None = None,
        **kwargs
    ):
        def func(data: Item, p: UpdaterParams) -> None:
            cmpt = data.components.get('points', None)
            if cmpt is None or not isinstance(cmpt, Cmpt_VPoints):
                return  # pragma: no cover
            if not cmpt.has():
                return  # pragma: no cover

            lower, higher = bound_func(p)

            if self.lag_ratio != 0:
                if lower <= 0 and higher >= 1:
                    return

                if lower == higher and zero_bound is not None:
                    if p.extra_data is None:
                        p._updater.extra_data = cmpt.pointwise_become_partial(cmpt, zero_bound, zero_bound).copy()
                    else:
                        cmpt.become(p.extra_data)
                    return

            if not auto_close_path:
                cmpt.pointwise_become_partial(cmpt, lower, higher)     # pragma: no cover
            else:
                end_indices = np.array(cmpt.get_subpath_end_indices())
                begin_indices = np.array([0, *[indice + 2 for indice in end_indices[:-1]]])

                points = cmpt.get()
                cond1 = np.isclose(points[begin_indices], points[end_indices]).all(axis=1)

                cmpt.pointwise_become_partial(cmpt, lower, higher)

                points = cmpt.get().copy()
                cond2 = ~np.isclose(points[begin_indices], points[end_indices]).all(axis=1)
                where = np.where(cond1 & cond2)[0]

                if len(where) == 0:
                    return

                end_indices = end_indices[where]
                begin_indices = begin_indices[where]

                points[end_indices] = points[begin_indices]
                if end_indices[-1] == len(points) - 1:
                    end_indices = end_indices[:-1]
                points[end_indices + 1] = NAN_POINT

                cmpt.set(points)

        super().__init__(item, func, become_at_end=become_at_end, root_only=root_only, **kwargs)


class Create(ShowPartial):
    '''
    显示物件的创建过程
    '''
    label_color = C_LABEL_ANIM_IN

    def __init__(self, item: Item, auto_close_path: bool = True, **kwargs):
        super().__init__(item, lambda p: (0, p.alpha), auto_close_path=auto_close_path, zero_bound=0, **kwargs)


class Uncreate(ShowPartial):
    '''
    显示物件的销毁过程（:class:`Create` 的倒放）
    '''
    label_color = C_LABEL_ANIM_OUT

    def __init__(
        self,
        item: Item,
        hide_at_end: bool = True,
        auto_close_path: bool = True,
        **kwargs
    ):
        super().__init__(
            item,
            lambda p: (0, 1.0 - p.alpha),
            hide_at_end=hide_at_end,
            auto_close_path=auto_close_path,
            zero_bound=0,
            **kwargs
        )


class Destruction(ShowPartial):
    '''
    显示物件的销毁过程

    - 与 :class:`Uncreate` 方向相反
    '''
    def __init__(
        self,
        item: Item,
        hide_at_end: bool = True,
        auto_close_path: bool = True,
        **kwargs
    ):
        super().__init__(
            item,
            lambda p: (p.alpha, 1.0),
            hide_at_end=hide_at_end,
            auto_close_path=auto_close_path,
            zero_bound=1,
            **kwargs
        )


class DrawBorderThenFill(DataUpdater):
    '''
    画出边缘，然后填充颜色

    -   可以使用 ``stroke_radius`` 参数调整“画出边缘”时的描边粗细，在默认画面下的值是 0.01

        如果设置了 ``scale_with_camera`` 参数，描边粗细会随着 ``camera`` 大小的变化而调整，画面尺寸越小，描边越细
    '''
    label_color = C_LABEL_ANIM_IN

    def __init__(
        self,
        item: Item,
        *,
        duration: float = 2.0,
        stroke_radius: float = DEFAULT_DRAWBORDER_THENFILL_STROKE_RADIUS,
        scale_with_camera: bool = False,
        stroke_color: JAnimColor = None,
        rate_func: RateFunc = double_smooth,
        become_at_end: bool = False,
        root_only: bool = False,
        **kwargs
    ):
        super().__init__(
            item,
            self.updater,
            extra=self.create_extra_data,
            duration=duration,
            rate_func=rate_func,
            become_at_end=become_at_end,
            root_only=root_only,
            **kwargs
        )

        if scale_with_camera:
            stroke_radius *= self.timeline.camera.points.scaled_factor
        self.stroke_radius = stroke_radius
        self.stroke_color = stroke_color

    @dataclass
    class ExtraData:
        outline: VItem
        zero_data: VItem

    def create_extra_data(self, data: Item) -> VItem | None:
        if not isinstance(data, VItem):
            return None     # pragma: no cover
        data_copy = data.store()
        data_copy.radius.set(self.stroke_radius)
        data_copy.stroke.set(self.stroke_color, 1)
        data_copy.fill.set(alpha=0)
        return DrawBorderThenFill.ExtraData(data_copy, None)

    def updater(self, data: VItem, p: UpdaterParams) -> None:
        if p.extra_data is None:
            return  # pragma: no cover

        if self.lag_ratio != 0:
            if p.alpha >= 1:
                return
            if p.alpha <= 0:
                if p.extra_data.zero_data is None:
                    p.extra_data.zero_data = data.points.pointwise_become_partial(data.points, 0, 0).copy()
                else:
                    data.points.become(p.extra_data.zero_data)
                return

        outline = p.extra_data.outline
        index, subalpha = integer_interpolate(0, 2, p.alpha)

        if index == 0:
            data.restore(outline)
            data.points.pointwise_become_partial(data.points, 0, subalpha)
        else:
            data.interpolate(outline, data, subalpha)


class Write(DrawBorderThenFill):
    '''
    显示书写过程（对每个子物件应用 :class:`DrawBorderThenFill`）
    '''
    def __init__(
        self,
        item: Item,
        *,
        duration: float | None = None,
        lag_ratio: float | None = None,
        rate_func: RateFunc = linear,
        skip_null_items: bool = True,
        root_only: bool = False,
        **kwargs
    ):
        length = len([
            item
            for item in item.walk_self_and_descendants(root_only=root_only)
            if not skip_null_items or not item.is_null()
        ])
        if duration is None:
            duration = 1 if length < 15 else 2
        if lag_ratio is None:
            lag_ratio = min(4.0 / (length + 1.0), 0.2)

        super().__init__(
            item,
            duration=duration,
            lag_ratio=lag_ratio,
            rate_func=rate_func,
            skip_null_items=skip_null_items,
            root_only=root_only,
            **kwargs
        )


class ShowIncreasingSubsets(Animation):
    label_color = C_LABEL_ANIM_IN

    def __init__(
        self,
        group: Group[Item],
        *,
        int_func=round,
        show_at_begin: bool = True,
        hide_at_end: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.group = group
        self.int_func = int_func
        self.show_at_begin = show_at_begin
        self.hide_at_end = hide_at_end

    def _time_fixed(self) -> None:
        if self.show_at_begin:
            self.timeline.schedule(self.t_range.at, self.group.show)
        if self.hide_at_end:
            self.timeline.schedule(self.t_range.end, self.group.hide)

        apprs = self.timeline.item_appearances

        self.i_apprs = [
            (i, [apprs[item] for item in child.walk_self_and_descendants()])
            for i, child in enumerate(self.group)
        ]
        self.n_children = len(self.group)
        self.timeline.add_additional_render_calls_callback(self.t_range, self.additional_callback)

    def additional_callback(self):
        global_t = Animation.global_t_ctx.get()
        alpha = self.get_alpha_on_global_t(global_t)
        for i, apprs in self.i_apprs:
            self.index = int(self.int_func(alpha * self.n_children))
            if not self.is_item_visible(i):
                for appr in apprs:
                    appr.render_disabled = True
        return []

    def is_item_visible(self, i: int) -> bool:
        return i < self.index


class ShowSubitemsOneByOne(ShowIncreasingSubsets):
    label_color = C_LABEL_ANIM_INDICATION

    def __init__(
        self,
        group: Group,
        *,
        int_func=math.ceil,
        hide_at_end: bool = True,
        **kwargs
    ):
        super().__init__(group, int_func=int_func, hide_at_end=hide_at_end, **kwargs)

    def is_item_visible(self, i: int) -> bool:
        return i == self.index - 1
