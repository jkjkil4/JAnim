from __future__ import annotations

from typing import Literal, Self

import numpy as np

from janim.components.component import CmptInfo
from janim.components.vpoints import Cmpt_VPoints
from janim.constants import DEGREES, LEFT, ORIGIN, RIGHT, UP, WHITE
from janim.items.geometry.arc import Arc, Dot
from janim.items.points import Group, MarkedItem, Points
from janim.items.vitem import DashedVItem, VItem
from janim.typing import JAnimColor, Vect
from janim.utils.bezier import PathBuilder
from janim.utils.simple_functions import clip
from janim.utils.space_ops import (angle_of_vector, get_arc_length, get_norm,
                                   line_intersection, normalize)

type SupportsPointify = Vect | Points
type AngleQuadrant = tuple[Literal[-1, 1], Literal[-1, 1]]

DEFAULT_DASH_LENGTH = 0.1


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
        start, end = np.asarray(start), np.asarray(end)

        curr_start, curr_end = self.get_start_and_end()
        if np.isclose(curr_start, curr_end).all():
            # Handle null lines more gracefully
            self.update_by_attrs(start, end, buff=0, path_arc=self.path_arc)
            return self
        return super().put_start_and_end_on(start, end)

    def update_by_attrs(
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
        points = builder.get()

        # Apply buffer
        if buff > 0:
            arc_len = get_arc_length(get_norm(points[-1] - points[0]), path_arc)
            alpha = min(buff / arc_len, 0.5)
            points = self.partial_points(points, alpha, 1 - alpha)
        elif buff < 0:
            start_dir = normalize(self.start_direction_from_points(points))
            end_dir = normalize(self.end_direction_from_points(points))
            if path_arc == 0:
                points[0] += start_dir * buff
                points[-1] -= end_dir * buff
            else:
                points = np.vstack([
                    [points[0] + start_dir * buff, points[0] + start_dir * (0.5 * buff)],
                    points,
                    [points[-1] - end_dir * (0.5 * buff), points[-1] - end_dir * buff]
                ])

        self.set(points)
        return self

    def update_points_by_attrs(self, *args, **kwargs) -> Self:
        from janim.utils.deprecation import deprecated
        deprecated(
            'update_points_by_attrs',
            'update_by_attrs',
            remove=(4, 3)
        )
        return self.update_by_attrs(*args, **kwargs)

    def set_buff(self, buff: float) -> Self:
        self.update_by_attrs(buff=buff)
        return self

    def set_path_arc(self, path_arc: float) -> Self:
        self.update_by_attrs(path_arc=path_arc)
        return self

    def set_start_and_end(self, start: SupportsPointify, end: SupportsPointify) -> Self:
        start, end = self.pointify_start_and_end(start, end)
        self.update_by_attrs(start=start, end=end)
        return self

    @staticmethod
    def pointify_start_and_end(start: SupportsPointify, end: SupportsPointify) -> tuple[np.ndarray, np.ndarray]:
        # If either start or end are Mobjects, this
        # gives their centers
        rough_start = Cmpt_VPoints_LineImpl.pointify(start)
        rough_end = Cmpt_VPoints_LineImpl.pointify(end)
        if np.isclose(rough_start, rough_end).all():
            rough_end[0] += 1e-6
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
        return get_arc_length(get_norm(self.vector), self.path_arc)


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
        self.points.update_by_attrs(start, end, buff, path_arc)


class Cmpt_VPoints_DashedLineImpl[ItemT](Cmpt_VPoints_LineImpl[ItemT], impl=True):
    '''
    在虚线中，对 :class:`~.Cmpt_VPoints` 的进一步实现
    '''
    def get_start(self) -> np.ndarray:
        assert self.bind is not None
        sub = self.bind.at_item.children[0]
        assert isinstance(sub, VItem)
        return sub.points.get_start()

    def get_end(self) -> np.ndarray:
        assert self.bind is not None
        sub = self.bind.at_item.children[-1]
        assert isinstance(sub, VItem)
        return sub.points.get_end()


class DashedLine(Line, Group[VItem]):
    '''
    虚线

    - ``dash_length``: 每段虚线的长度
    - ``dashed_ratio``: 虚线段的占比，默认为 ``0.5``，即虚线段与空白段长度相等，但可能因为虚线段描边存在粗细而导致视觉上空白长度略小
    '''
    def __init__(
        self,
        start: Vect | Points = LEFT,
        end: Vect | Points = RIGHT,
        *,
        dash_length: float = DEFAULT_DASH_LENGTH,
        dashed_ratio: float = 0.5,
        **kwargs
    ) -> None:
        self.dash_length = dash_length
        self.dashed_ratio = dashed_ratio
        super().__init__(start, end, **kwargs)
        dashes = DashedVItem(
            self,
            num_dashes=self._calculate_num_dashes(),
            dashed_ratio=dashed_ratio,
        )
        self.points.clear()
        self.add(*dashes)

    def _calculate_num_dashes(self) -> int:
        '''
        基于线段长度计算所需虚线段的数量
        '''
        return max(
            2,
            int(np.ceil((self.points.length / self.dash_length) * self.dashed_ratio)),
        )


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


class Elbow(MarkedItem, VItem):
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
        self.mark.set_points([ORIGIN])


# borrowed from https://github.com/ManimCommunity/manim/blob/main/manim/mobject/geometry/line.py
class Angle(MarkedItem, VItem):
    '''
    一个圆弧或直角标记对象，用于表示两条线之间的夹角

    - ``radius``: 圆弧的半径

    - ``quadrant``:
        | 由两个整数构成的序列，用于确定应使用哪一个象限为基准；
        | 第一个值表示在第一条线上以终点(1)或起点(-1)为基准，第二个值同理作用于第二条线；
        | 可选值包括： ``(1, 1)``, ``(1, -1)``, ``(-1, 1)``, ``(-1, -1)``

    - ``other_angle``:
        | 在两个可能的夹角之间切换。默认 ``False``，则弧线从 ``line1`` 到 ``line2`` 按逆时针绘制；
        | 如果为 ``True``，则按顺时针方向绘制

    - ``dot``: 是否在弧线上添加一个点，通常用于指示直角

    - ``dot_radius``: 点的半径，默认为弧半径的 ``1/10``

    - ``dot_distance``: 点到圆心的相对距离，其中 ``0`` 表示在圆心处，``1`` 表示在圆弧上，默认为 ``0.55``

    - ``dot_color``: 点的颜色

    - ``elbow``: 是否使用直角标记的形式，参考 :class:`RightAngle` 类
    '''
    def __init__(
        self,
        line1: Line,
        line2: Line,
        radius: float | None = None,
        quadrant: AngleQuadrant = (1, 1),
        other_angle: bool = False,
        dot: bool = False,
        dot_radius: float | None = None,
        dot_distance: float = 0.55,
        dot_color: JAnimColor = WHITE,
        elbow: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.lines = (line1, line2)
        self.quadrant = quadrant
        self.dot_distance = dot_distance
        self.elbow = elbow
        inter = line_intersection(
            [line1.points.get_start(), line1.points.get_end()],
            [line2.points.get_start(), line2.points.get_end()]
        )

        if radius is None:
            if quadrant[0] == 1:
                dist_1 = np.linalg.norm(line1.points.get_end() - inter)
            else:
                dist_1 = np.linalg.norm(line1.points.get_start() - inter)
            if quadrant[1] == 1:
                dist_2 = np.linalg.norm(line2.points.get_end() - inter)
            else:
                dist_2 = np.linalg.norm(line2.points.get_start() - inter)
            if np.minimum(dist_1, dist_2) < 0.6:
                radius = (2 / 3) * np.minimum(dist_1, dist_2)
            else:
                radius = 0.4

        anchor_angle_1 = inter + quadrant[0] * radius * line1.points.unit_vector
        anchor_angle_2 = inter + quadrant[1] * radius * line2.points.unit_vector

        if elbow:
            anchor_middle = (
                inter
                + quadrant[0] * radius * line1.points.unit_vector
                + quadrant[1] * radius * line2.points.unit_vector
            )
            angle_item = Elbow(**kwargs)
            angle_item.points.set_as_corners([
                anchor_angle_1, anchor_middle, anchor_angle_2
            ])
        else:
            angle_1 = angle_of_vector(anchor_angle_1 - inter)
            angle_2 = angle_of_vector(anchor_angle_2 - inter)

            if not other_angle:
                start_angle = angle_1
                if angle_2 > angle_1:
                    angle_fin = angle_2 - angle_1
                else:
                    angle_fin = 2 * np.pi - (angle_1 - angle_2)
            else:
                start_angle = angle_1
                if angle_2 < angle_1:
                    angle_fin = -angle_1 + angle_2
                else:
                    angle_fin = -2 * np.pi + (angle_2 - angle_1)

            self.angle_value = angle_fin

            angle_item = Arc(
                radius=radius,
                angle=self.angle_value,
                start_angle=start_angle,
                arc_center=inter,
                **kwargs,
            )

            if dot:
                if dot_radius is None:
                    dot_radius = radius / 10
                else:
                    self.dot_radius = dot_radius
                right_dot = Dot(ORIGIN, radius=dot_radius, color=dot_color)
                dot_anchor = (
                    inter
                    + (angle_item.points.box.center - inter)
                    / np.linalg.norm(angle_item.points.box.center - inter)
                    * radius
                    * dot_distance
                )
                right_dot.points.move_to(dot_anchor)
                self.add(right_dot)

        self.points.set(angle_item.points.get())
        self.mark.set_points([inter])

    def get_lines(self) -> Group:
        '''
        返回一个包含构成该角的两个 :class:`~.Line` 的 :class:`~.Group` 对象
        '''
        return Group(*self.lines)

    def get_value(self, degrees: bool = False) -> float:
        '''
        获取该角的数值

        - ``degrees``: 是否以角度的形式返回，默认为 ``False``，即弧度制
        '''
        return self.angle_value / DEGREES if degrees else self.angle_value

    @staticmethod
    def from_three_points(
        A: Vect, B: Vect, C: Vect, **kwargs
    ) -> Angle:
        '''
        由三点构造一个角，表示 ∠ABC，点 ``B`` 为角的顶点
        '''
        return Angle(Line(B, A), Line(B, C), **kwargs)


class RightAngle(Angle):
    '''
    一个用于表示直角的 :class:`Elbow` 样式的对象（L 形折角）

    - ``length``: 直角标记的边长
    '''
    def __init__(
        self,
        line1: Line,
        line2: Line,
        length: float | None = None,
        **kwargs,
    ) -> None:
        super().__init__(line1, line2, radius=length, elbow=True, **kwargs)


# TODO: CubicBezier
