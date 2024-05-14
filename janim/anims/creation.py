
from typing import Callable

import numpy as np

from janim.anims.updater import DataUpdater, UpdaterParams
from janim.components.vpoints import Cmpt_VPoints
from janim.constants import (C_LABEL_ANIM_ABSTRACT, C_LABEL_ANIM_IN,
                             C_LABEL_ANIM_OUT, NAN_POINT)
from janim.items.item import Item
from janim.items.vitem import VItem
from janim.typing import JAnimColor
from janim.utils.bezier import integer_interpolate
from janim.utils.rate_functions import RateFunc, double_smooth, linear


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
        **kwargs
    ):
        def func(data: Item, p: UpdaterParams) -> None:
            cmpt = data.components.get('points', None)
            if cmpt is None or not isinstance(cmpt, Cmpt_VPoints):
                return  # pragma: no cover
            if not cmpt.has():
                return  # pragma: no cover

            if not auto_close_path:
                cmpt.pointwise_become_partial(cmpt, *bound_func(p))     # pragma: no cover
            else:
                end_indices = np.array(cmpt.get_subpath_end_indices())
                begin_indices = np.array([0, *[indice + 2 for indice in end_indices[:-1]]])

                points = cmpt.get()
                cond1 = np.isclose(points[begin_indices], points[end_indices]).all(axis=1)

                cmpt.pointwise_become_partial(cmpt, *bound_func(p))

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
        super().__init__(item, lambda p: (0, p.alpha), auto_close_path=auto_close_path, **kwargs)


class Uncreate(ShowPartial):
    '''
    显示物件的销毁过程（:class:`Create` 的倒放）
    '''
    label_color = C_LABEL_ANIM_OUT

    def __init__(
        self,
        item: Item,
        show_at_end: bool = False,
        auto_close_path: bool = True,
        **kwargs
    ):
        super().__init__(
            item,
            lambda p: (0, 1.0 - p.alpha),
            show_at_end=show_at_end,
            auto_close_path=auto_close_path,
            **kwargs
        )


class DrawBorderThenFill(DataUpdater):
    '''
    画出边缘，然后填充颜色
    '''
    label_color = C_LABEL_ANIM_IN

    def __init__(
        self,
        item: Item,
        *,
        duration: float = 2.0,
        stroke_radius: float = 0.01,
        stroke_color: JAnimColor = None,
        rate_func: RateFunc = double_smooth,
        become_at_end: bool = False,
        root_only: bool = False,
        **kwargs
    ):
        super().__init__(
            item,
            self.updater,
            duration=duration,
            rate_func=rate_func,
            become_at_end=become_at_end,
            root_only=root_only,
            **kwargs
        )
        self.stroke_radius = stroke_radius
        self.stroke_color = stroke_color

    def create_extra_data(self, data: Item) -> VItem | None:
        if not isinstance(data, VItem):
            return None     # pragma: no cover
        data_copy = data.store()
        data_copy.radius.set(self.stroke_radius)
        data_copy.stroke.set(self.stroke_color, 1)
        data_copy.fill.set(alpha=0)
        return data_copy

    def updater(self, data: VItem, p: UpdaterParams) -> None:
        if p.extra_data is None:
            return  # pragma: no cover
        outline = p.extra_data
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
            for item in (
                [self.item]
                if root_only
                else item.walk_self_and_descendants()
            )
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
