from __future__ import annotations

import math
from typing import Self

import numpy as np

from janim.components.component import CmptInfo
from janim.components.vpoints import Cmpt_VPoints
from janim.constants import LEFT, ORIGIN, RIGHT, UP
from janim.items.points import Points
from janim.items.vitem import VItem
from janim.typing import Vect
from janim.utils.bezier import PathBuilder
from janim.utils.simple_functions import clip
from janim.utils.space_ops import angle_of_vector, get_norm, normalize


class _Cmpt_VPoints_LineImpl[ItemT](Cmpt_VPoints[ItemT], impl=True):
    '''
    在线段中，对 :class:`~.Cmpt_VPoints` 的进一步实现
    '''
    def put_start_and_end_on(self, start: Vect, end: Vect) -> Self:
        at_item: Line = self.bind.at_item
        curr_start, curr_end = self.get_start_and_end()
        if np.isclose(curr_start, curr_end).all():
            # Handle null lines more gracefully
            at_item.update_points_by_attrs(start, end, buff=0, path_arc=at_item.path_arc)
            return self
        return self.put_start_and_end_on(start, end)


class Line(VItem):
    '''
    线段

    传入 ``start``, ``end`` 为线段起点终点

    - ``buff``: 线段两端的空余量，默认为 ``0``
    - ``path_arc``: 表示线段的弯曲角度
    '''
    points = CmptInfo(_Cmpt_VPoints_LineImpl[Self])

    def __init__(
        self,
        start: Vect | Points = LEFT,
        end: Vect | Points = RIGHT,
        *,
        buff: float = 0,
        path_arc: float = 0,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.path_arc = path_arc
        self.buff = buff
        self.set_start_and_end(start, end)

    def update_points_by_attrs(self) -> Self:
        builder = PathBuilder(start_point=self.start)
        builder.arc_to(self.end, self.path_arc)
        self.points.set(builder.get())

        # Apply buffer
        if self.buff > 0:
            length = self.arc_length
            alpha = min(self.buff / length, 0.5)
            self.points.pointwise_become_partial(self.points, alpha, 1 - alpha)
        return self

    def set_buff(self, new_value: float) -> Self:
        self.buff = new_value
        self.update_points_by_attrs()
        return self

    def set_path_arc(self, new_value: float) -> Self:
        self.path_arc = new_value
        self.update_points_by_attrs()
        return self

    def set_start_and_end(self, start: Vect | Points, end: Vect | Points):
        # If either start or end are Mobjects, this
        # gives their centers
        rough_start = self.pointify(start)
        rough_end = self.pointify(end)
        vect = normalize(rough_end - rough_start)
        # Now that we know the direction between them,
        # we can find the appropriate boundary point from
        # start and end, if they're mobjects
        self.start = self.pointify(start, vect)
        self.end = self.pointify(end, -vect)
        self.update_points_by_attrs()

    def pointify(
        self,
        item_or_point: Vect | Points,
        direction: Vect | None = None
    ) -> Vect:
        """
        Take an argument passed into Line (or subclass) and turn
        it into a 3d point.
        """
        if isinstance(item_or_point, Points):
            item = item_or_point
            if direction is None:
                return item.points.box.center
            else:
                return item.points.box.get_continuous(direction)
        else:
            point = item_or_point
            result = np.zeros(3)
            result[:len(point)] = point
            return result

    @property
    def vector(self) -> Vect:
        return self.points.get_end() - self.points.get_start()

    @property
    def unit_vector(self) -> Vect:
        return normalize(self.vector)

    @property
    def angle(self) -> float:
        return angle_of_vector(self.vector)

    def get_projection(self, point: Vect) -> Vect:
        """
        Return projection of a point onto the line
        """
        unit_vect = self.unit_vector
        start = self.points.get_start()
        return start + np.dot(point - start, unit_vect) * unit_vect

    def get_slope(self) -> float:
        return np.tan(self.angle)

    def set_angle(self, angle: float, about_point: Vect | None = None) -> Self:
        if about_point is None:
            about_point = self.points.get_start()
        self.points.rotate(
            angle - self.angle,
            about_point=about_point,
        )
        return self

    def set_length(self, length: float, **kwargs):
        self.points.scale(length / self.length, **kwargs)
        return self

    @property
    def length(self) -> float:
        return get_norm(self.vector)

    @property
    def arc_length(self) -> float:
        arc_len = get_norm(self.vector)
        if self.path_arc > 0:
            arc_len *= self.path_arc / (2 * math.sin(self.path_arc / 2))
        return arc_len


# TODO: DashedLine


class TangentLine(Line):
    '''
    切线

    - 传入 ``vitem`` 表示需要做切线的物件，``alpha`` 表示切点在 ``vitem`` 上的比例
    - ``length``: 切线长度
    - ``d_alpha``: 精细程度，越小越精细（默认 ``1e-6``）
    '''
    def __init__(
        self,
        vitem: VItem,
        alpha: float,
        length: float = 1,
        *,
        d_alpha: float = 1e-6,
        **kwargs
    ) -> None:
        a1 = clip(alpha - d_alpha, 0, 1)
        a2 = clip(alpha + d_alpha, 0, 1)
        super().__init__(vitem.points.pfp(a1), vitem.points.pfp(a2), **kwargs)
        self.points.scale(length / self.length)


class Elbow(VItem):
    '''
    折线（一般用作直角符号）

    - width 表示宽度
    - angle 表示角度
    '''
    def __init__(
        self,
        width: float = 0.2,
        angle: float = 0,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.points.set_as_corners([UP, UP + RIGHT, RIGHT])
        self.points.set_width(width, about_point=ORIGIN)
        self.points.rotate(angle, about_point=ORIGIN)


# TODO: CubicBezier
