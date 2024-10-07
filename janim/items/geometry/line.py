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

type SupportsPointify = Vect | Points


class Cmpt_VPoints_LineImpl[ItemT](Cmpt_VPoints[ItemT]):
    '''
    在线段中，对 :class:`~.Cmpt_VPoints` 的进一步实现
    '''
    def copy(self) -> Self:
        copy_cmpt = super().copy()
        copy_cmpt.start = self.start.copy()
        copy_cmpt.end = self.end.copy()
        # buff 和 path_arc 已经通过 copy.copy(self) 复制
        return copy_cmpt

    def become(self, other: Cmpt_VPoints_LineImpl) -> Self:
        super().become(other)
        self.start = other.start.copy()
        self.end = other.end.copy()
        self.buff = other.buff
        self.path_arc = other.path_arc
        return self

    def not_changed(self, other) -> bool:
        return super().not_changed(other)

    def put_start_and_end_on(self, start: Vect, end: Vect) -> Self:
        curr_start, curr_end = self.get_start_and_end()
        if np.isclose(curr_start, curr_end).all():
            # Handle null lines more gracefully
            self.update_points_by_attrs(start, end, buff=0, path_arc=self.path_arc)
            return self
        return super().put_start_and_end_on(start, end)

    def update_points_by_attrs(
        self,
        start: np.ndarray | None = None,
        end: np.ndarray | None = None,
        buff: float | None = None,
        path_arc: float | None = None
    ) -> Self:
        if start is None:
            start = self.start
            assert start is not None
        else:
            self.start = start

        if end is None:
            end = self.end
            assert end is not None
        else:
            self.end = end

        if buff is None:
            buff = self.buff
            assert buff is not None
        else:
            self.buff = buff

        if path_arc is None:
            path_arc = self.path_arc
            assert path_arc is not None
        else:
            self.path_arc = path_arc

        builder = PathBuilder(start_point=start)
        builder.arc_to(end, path_arc)
        self.set(builder.get())

        # Apply buffer
        if buff > 0:
            alpha = min(buff / self.arc_length, 0.5)
            self.pointwise_become_partial(self, alpha, 1 - alpha)
        return self

    def set_buff(self, buff: float) -> Self:
        self.update_points_by_attrs(buff=buff)
        return self

    def set_path_arc(self, path_arc: float) -> Self:
        self.update_points_by_attrs(path_arc=path_arc)
        return self

    def set_start_and_end(self, start: SupportsPointify, end: SupportsPointify) -> Self:
        start, end = self.pointify_start_and_end(start, end)
        self.update_points_by_attrs(start=start, end=end)
        return self

    @staticmethod
    def pointify_start_and_end(start: SupportsPointify, end: SupportsPointify) -> tuple[np.ndarray, np.ndarray]:
        # If either start or end are Mobjects, this
        # gives their centers
        rough_start = Cmpt_VPoints_LineImpl.pointify(start)
        rough_end = Cmpt_VPoints_LineImpl.pointify(end)
        vect = normalize(rough_end - rough_start)
        # Now that we know the direction between them,
        # we can find the appropriate boundary point from
        # start and end, if they're items
        return (
            Cmpt_VPoints_LineImpl.pointify(start, vect),
            Cmpt_VPoints_LineImpl.pointify(end, -vect)
        )

    @staticmethod
    def pointify(
        item_or_data_or_point: SupportsPointify,
        direction: Vect | None = None
    ) -> np.ndarray:
        """
        Take an argument passed into Line (or subclass) and turn
        it into a 3d point.
        """
        if isinstance(item_or_data_or_point, Points):
            cmpt = item_or_data_or_point.points

            if direction is None:
                return cmpt.box.center
            else:
                return cmpt.box.get_continuous(direction)
        else:
            point = item_or_data_or_point
            result = np.zeros(3)
            result[:len(point)] = point
            return result

    @property
    def vector(self) -> np.ndarray:
        return self.get_end() - self.get_start()

    @property
    def unit_vector(self) -> np.ndarray:
        return normalize(self.vector)

    @property
    def angle(self) -> float:
        return angle_of_vector(self.vector)

    def get_projection(self, point: Vect) -> np.ndarray:
        """
        Return projection of a point onto the line
        """
        unit_vect = self.unit_vector
        start = self.get_start()
        return start + np.dot(point - start, unit_vect) * unit_vect

    def get_slope(self) -> float:
        return np.tan(self.angle)

    def set_angle(self, angle: float, about_point: Vect | None = None) -> Self:
        if about_point is None:
            about_point = self.get_start()
        self.rotate(
            angle - self.angle,
            about_point=about_point,
        )
        return self

    def set_length(self, length: float, **kwargs):
        self.scale(length / self.length, **kwargs)
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


class Line(VItem):
    '''
    线段

    传入 ``start``, ``end`` 为线段起点终点

    - ``buff``: 线段两端的空余量，默认为 ``0``
    - ``path_arc``: 表示线段的弯曲角度
    '''
    points = CmptInfo(Cmpt_VPoints_LineImpl[Self])

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

        start, end = self.points.pointify_start_and_end(start, end)
        self.points.update_points_by_attrs(start, end, buff, path_arc)


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
        self.points.scale(length / self.points.length)


class Elbow(VItem):
    '''
    折线（一般用作直角符号）

    - ``width`` 表示宽度
    - ``angle`` 表示角度
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
