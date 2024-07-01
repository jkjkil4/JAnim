from __future__ import annotations

from typing import Callable

import numpy as np

from janim.anims.animation import Animation, RenderCall
from janim.anims.transform import Transform
from janim.constants import C_LABEL_ANIM_ABSTRACT, C_LABEL_ANIM_IN, PI
from janim.items.geometry.arrow import Arrow
from janim.items.points import Points


class GrowFromPoint(Transform):
    '''
    从指定的位置放大显现
    '''
    label_color = C_LABEL_ANIM_IN

    def __init__(
        self,
        item: Points,
        point: np.ndarray,
        *,
        hide_src: bool = True,
        **kwargs
    ):
        self.point = point
        self.start_item = item.copy()
        self.start_item.points.scale(0).move_to(point)
        super().__init__(self.start_item, item, hide_src=hide_src, **kwargs)

    def anim_init(self) -> None:
        super().anim_init()
        if self.hide_src:
            self.timeline.schedule(self.global_range.at, self.target_item.hide, root_only=self.root_only)


class GrowFromCenter(GrowFromPoint):
    '''从物件的中心放大显现'''
    def __init__(self, item: Points, **kwargs):
        point = item.points.box.center
        super().__init__(item, point, **kwargs)


class GrowFromEdge(GrowFromPoint):
    '''从物件的指定边角放大显现'''
    def __init__(self, item: Points, edge: np.ndarray, **kwargs):
        point = item.points.box.get(edge)
        super().__init__(item, point, **kwargs)


class SpinInFromNothing(GrowFromCenter):
    '''从物件的中心旋转半圈放大显现'''
    def __init__(self, item: Points, *, path_arc=PI, **kwargs):
        super().__init__(item, path_arc=path_arc, **kwargs)


class GrowArrowByBoundFunc(Animation):
    ''':class:`GrowArrow` 和 :class:`GrowDoubleArrow` 的基类'''
    label_color = C_LABEL_ANIM_ABSTRACT

    def __init__(
        self,
        arrow: Arrow,
        bound_func: Callable[[float], tuple[float, float]],
        *,
        hide_at_begin: bool = True,
        show_at_end: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.arrow = arrow
        self.bound_func = bound_func
        self.hide_at_begin = hide_at_begin
        self.show_at_end = show_at_end

        self.timeline.track_item_and_descendants(arrow)

    def anim_init(self) -> None:
        self.arrow_copy = self.arrow.copy()
        self.arrow_anim = self.arrow.copy()

        self.set_render_call_list([
            RenderCall(
                item.depth,
                item.render
            )
            for item in self.arrow_anim.walk_self_and_descendants()
        ])

        if self.hide_at_begin:
            self.timeline.schedule(self.global_range.at, self.arrow.hide)
        if self.show_at_end:
            self.timeline.schedule(self.global_range.end, self.arrow.show)

    def anim_on_alpha(self, alpha: float) -> None:
        self.arrow_anim.points.pointwise_become_partial(self.arrow_copy, *self.bound_func(alpha))
        self.arrow_anim.place_tip()


class GrowArrow(GrowArrowByBoundFunc):
    '''显示箭头的显现过程，从开头到结尾画出，并自动调整箭头标志位置'''
    label_color = C_LABEL_ANIM_IN

    def __init__(self, arrow: Arrow, **kwargs):
        super().__init__(arrow, lambda alpha: (0, alpha), **kwargs)


class GrowDoubleArrow(GrowArrowByBoundFunc):
    '''
    显示箭头的显现过程，默认从中间向两边显现，并自动调整箭头标志位置

    - 传入 ``start_ratio`` （默认 ``0.5``） 可以调整开始的位置
    '''
    label_color = C_LABEL_ANIM_IN

    def __init__(self, arrow: Arrow, start_ratio: float = 0.5, **kwargs):
        super().__init__(
            arrow,
            lambda alpha: (start_ratio * (1 - alpha), 1 - (1 - start_ratio) * (1 - alpha)),
            **kwargs
        )
