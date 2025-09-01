from __future__ import annotations

from typing import Callable

import numpy as np

from janim.anims.updater import DataUpdater, GroupUpdater, UpdaterParams
from janim.constants import (C_LABEL_ANIM_ABSTRACT, C_LABEL_ANIM_IN,
                             C_LABEL_ANIM_OUT, PI)
from janim.items.geometry.arrow import Arrow
from janim.items.points import Points
from janim.utils.rate_functions import rush_into


class GrowFromPoint(DataUpdater[Points]):
    '''
    从指定的位置放大显现
    '''

    label_color = C_LABEL_ANIM_IN

    def __init__(
        self,
        item: Points,
        point: np.ndarray,
        root_only: bool = False,
        **kwargs
    ):
        self.point = point
        super().__init__(
            item,
            lambda data, p: data.points.scale(p.alpha, about_point=point),
            root_only=root_only,
            become_at_end=False,    # 因为最终状态和原状态没有区别，所以不需要 become_at_end，并且也不暴露参数
            **kwargs,
        )


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


class ShrinkToPoint(DataUpdater[Points]):
    '''
    缩小到指定的位置消失
    '''

    label_color = C_LABEL_ANIM_OUT

    def __init__(
        self,
        item: Points,
        point: np.ndarray,
        root_only: bool = False,
        hide_at_end: bool = True,
        become_at_end: bool = False,
        **kwargs
    ):
        self.point = point
        super().__init__(
            item,
            lambda data, p: data.points.scale((1 - p.alpha), about_point=point),
            root_only=root_only,
            hide_at_end=hide_at_end,
            become_at_end=become_at_end,
            **kwargs,
        )


class ShrinkToCenter(ShrinkToPoint):
    '''缩小到物件的中心消失'''

    def __init__(self, item: Points, **kwargs):
        point = item.points.box.center
        super().__init__(item, point, **kwargs)


class ShrinkToEdge(ShrinkToPoint):
    '''缩小到物件的指定边角消失'''

    def __init__(self, item: Points, edge: np.ndarray, **kwargs):
        point = item.points.box.get(edge)
        super().__init__(item, point, **kwargs)


class SpinInFromNothing(GrowFromCenter):
    '''从物件的中心旋转半圈放大显现'''

    def __init__(self, item: Points, *, path_arc=PI / 2, **kwargs):
        super().__init__(item, **kwargs)
        self.add_post_updater(
            lambda data, p: data.points.rotate(
                path_arc * (p.alpha - 1), about_point=self.point
            )
        )


class SpinOutToNothing(ShrinkToCenter):
    '''向物件的中心旋转半圈缩小消失'''

    def __init__(self, item: Points, *, path_arc=PI / 2, rate_func=rush_into, **kwargs):
        super().__init__(item, rate_func=rate_func, **kwargs)
        self.add_post_updater(
            lambda data, p: data.points.rotate(
                path_arc * p.alpha, about_point=self.point
            )
        )


class GrowArrowByBoundFunc(GroupUpdater):
    ''':class:`GrowArrow` 和 :class:`GrowDoubleArrow` 的基类'''

    label_color = C_LABEL_ANIM_ABSTRACT

    def __init__(
        self, arrow: Arrow, bound_func: Callable[[float], tuple[float, float]], **kwargs
    ):
        super().__init__(arrow, self.updater, **kwargs)
        self.arrow = arrow
        self.bound_func = bound_func

    def updater(self, arrow: Arrow, p: UpdaterParams) -> None:
        arrow.points.pointwise_become_partial(arrow, *self.bound_func(p.alpha))
        arrow.place_tip()


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
            lambda alpha: (
                start_ratio * (1 - alpha),
                1 - (1 - start_ratio) * (1 - alpha),
            ),
            **kwargs,
        )
