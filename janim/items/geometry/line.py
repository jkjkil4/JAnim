from __future__ import annotations

from typing import Iterable, Literal, Self

import numpy as np

from janim.components.component import CmptInfo
from janim.components.points import Cmpt_Points
from janim.components.vpoints import Cmpt_VPoints
from janim.constants import DEGREES, LEFT, ORIGIN, RIGHT, UP, WHITE
from janim.items.geometry import GeometryShape
from janim.items.geometry.arc import Arc, Dot
from janim.items.group import Group
from janim.items.points import MarkedItem, Points
from janim.items.vitem import DashedVItem, DashedVItemByRatio, VItem
from janim.typing import JAnimColor, Vect
from janim.utils.bezier import PathBuilder
from janim.utils.simple_functions import clip
from janim.utils.space_ops import (angle_of_vector, get_arc_length, get_norm,
                                   line_intersection, normalize)

type AngleQuadrant = tuple[Literal[-1, 1], Literal[-1, 1]]
type LineBuff = float | tuple[float, float]

DEFAULT_DASH_LENGTH = 0.1


class Cmpt_VPoints_LineImpl[ItemT](Cmpt_VPoints[ItemT], impl=True):
    """
    在线段中，对 :class:`~.Cmpt_VPoints` 的进一步实现
    """

    @property
    def _path_arc(self) -> float:
        item: Line = self.bind.at_item
        return item.reshape_params['path_arc']

    def put_start_and_end_on(self, start: Vect, end: Vect) -> Self:
        start, end = np.asarray(start), np.asarray(end)

        curr_start, curr_end = self.get_start_and_end()
        if np.isclose(curr_start, curr_end).all():
            # 如果当前的 curr_start/curr_end 是同一点，会导致 put_start_and_end_on 中没法缩放匹配至 start/end
            # 因此这种情况下直接重设点数据
            # 不直接使用 reshape 是为了避免影响参数记忆
            self.set(Line.build_points(start, end, 0, self._path_arc))
        else:
            super().put_start_and_end_on(start, end)

        return self

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
        return get_arc_length(get_norm(self.vector), self._path_arc)

    # region deprecated

    # 仅为了方便 deprecated 函数 self.bind.at_item 的类型注解，不作为长期 API
    @property
    def _item(self) -> Line:
        return self.bind.at_item

    def update_by_attrs(self, start=None, end=None, buff=None, path_arc=None) -> Self:
        from janim.utils.deprecation import deprecated
        deprecated(
            '.points.update_by_attrs',
            '.reshape',
            remove=(4, 4)
        )
        self._item.reshape(start, end, buff=buff, path_arc=path_arc)
        return self

    def update_points_by_attrs(self, start=None, end=None, buff=None, path_arc=None) -> Self:
        from janim.utils.deprecation import deprecated
        deprecated(
            '.points.update_points_by_attrs',
            '.reshape',
            remove=(4, 3)
        )
        self._item.reshape(start, end, buff=buff, path_arc=path_arc)
        return self

    def set_buff(self, buff: LineBuff) -> Self:
        from janim.utils.deprecation import deprecated
        deprecated(
            '.points.set_buff',
            '.set_buff',
            remove=(4, 4)
        )
        self._item.set_buff(buff)
        return self

    def set_path_arc(self, path_arc: float) -> Self:
        from janim.utils.deprecation import deprecated
        deprecated(
            '.points.set_path_arc',
            '.set_path_arc',
            remove=(4, 4)
        )
        self._item.set_path_arc(path_arc)
        return self

    def set_start_and_end(self, start: Points | Vect, end: Points | Vect) -> Self:
        from janim.utils.deprecation import deprecated
        deprecated(
            '.points.set_start_and_end',
            '.set_start_and_end',
            remove=(4, 4)
        )
        self._item.set_start_and_end(start, end)
        return self

    @staticmethod
    def pointify_start_and_end(*args) -> tuple[np.ndarray, np.ndarray]:
        from janim.utils.deprecation import deprecated
        deprecated(
            'Cmpt_VPoints_LineImpl.pointify_start_and_end',
            'Line.pointify_start_and_end',
            remove=(4, 4)
        )
        return Line.pointify_start_and_end(*args)

    @staticmethod
    def pointify(input, direction=None) -> np.ndarray:
        from janim.utils.deprecation import deprecated
        deprecated(
            'Cmpt_VPoints_LineImpl.pointify',
            'Line.pointify',
            remove=(4, 4)
        )
        if isinstance(input, Points):
            input = input.points.box
        return Line.pointify(input, direction)

    # endregion


class Line(GeometryShape):
    """
    线段

    :param start: 线段起点，可为坐标向量或 :class:`~.Points` 对象；默认为 ``LEFT``
    :param end: 线段终点，可为坐标向量或 :class:`~.Points` 对象；默认为 ``RIGHT``
    :param buff: 线段两端的空余量，可为单个数值或者一个元组表示两端的空余量；可用负值表示向外延伸
    :param path_arc: 线段的弯曲弧度，默认为 ``0``；``0`` 表示直线，非零则是一段圆弧
    :param \\*\\*kwargs: 其它参数
    """
    points = CmptInfo(Cmpt_VPoints_LineImpl[Self])

    def __init__(
        self,
        start: Vect | Points = LEFT,
        end: Vect | Points = RIGHT,
        *,
        buff: LineBuff = 0,
        path_arc: float = 0,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self._reshape(start, end, buff, path_arc)

    # region reshape-related

    def set_buff(self, buff: LineBuff) -> Self:
        self._reshape(buff=buff)
        return self

    def set_path_arc(self, path_arc: float) -> Self:
        self._reshape(path_arc=path_arc)
        return self

    def set_start_and_end(self, start: Points | Vect, end: Points | Vect) -> Self:
        self._reshape(start, end)
        return self

    # endregion

    # region reshape

    def _reshape(
        self,
        start: Points | Vect | None = None,
        end: Points | Vect | None = None,
        buff: LineBuff | None = None,
        path_arc: float | None = None
    ) -> None:
        # 如果 start 和 end 是 Points 物件，则转换为边界框对象，避免 memorize 持续持有对其它物件的引用
        def _item_to_box(x: Points | Vect | None) -> Cmpt_Points.BoundingBox | Vect | None:
            return x.points.box if isinstance(x, Points) else x
        start = _item_to_box(start)
        end = _item_to_box(end)

        start, end, buff, path_arc = self._reshape_memorize(start=start, end=end, buff=buff, path_arc=path_arc)
        start, end = self.pointify_start_and_end(start, end)
        self.points.set(self.build_points(start, end, buff, path_arc))

    def reshape(
        self,
        start: Points | Vect | None = None,
        end: Points | Vect | None = None,
        *,
        buff: LineBuff | None = None,
        path_arc: float | None = None
    ) -> Self:
        self._reshape(start, end, buff, path_arc)
        return self

    @staticmethod
    def build_points(start: np.ndarray, end: np.ndarray, buff: LineBuff, path_arc: float) -> np.ndarray:
        """
        构建线段的点数据

        基于起点、终点、两端空余量和弯曲弧度生成线段的点数组

        :param start: 线段的起点坐标
        :param end: 线段的终点坐标
        :param buff: 线段两端的空余量，可为单个数值或者一个元组表示两端的空余量；可用负值表示向外延伸
        :param path_arc: 线段的弯曲弧度；0 即为直线，非零则是一段圆弧
        :return: 线段的点数据数组
        """
        if isinstance(buff, Iterable):
            start_buff, end_buff = buff
        else:
            start_buff, end_buff = buff, buff

        builder = PathBuilder(start_point=start)
        builder.arc_to(end, path_arc)
        points = builder.get()

        # 处理正 buffer
        # 并且如果其中一个是负 buffer 的话，会因为 max(buff, 0) 而被保留在原始位置
        # 不被 partial_points 截断，到后面再继续处理负 buffer 逻辑
        if start_buff > 0 or end_buff > 0:
            arc_len = get_arc_length(get_norm(points[-1] - points[0]), path_arc)
            if arc_len > 0:
                alpha_start = min(max(start_buff, 0) / arc_len, 0.5)
                alpha_end = min(max(end_buff, 0) / arc_len, 0.5)
                points = Cmpt_VPoints.partial_points(points, alpha_start, 1 - alpha_end)
        # 处理负 buffer，即反向延伸
        # 得到 start_dir 和 end_dir 并根据这两个方向向外延伸
        if start_buff < 0 or end_buff < 0:
            start_dir = normalize(Cmpt_VPoints.start_direction_from_points(points))
            end_dir = normalize(Cmpt_VPoints.end_direction_from_points(points))
            if path_arc == 0:
                if start_buff < 0:
                    points[0] += start_dir * start_buff
                if end_buff < 0:
                    points[-1] -= end_dir * end_buff
            else:
                extra_points = [points]
                if start_buff < 0:
                    extra_points.insert(0, np.array([
                        points[0] + start_dir * start_buff,
                        points[0] + start_dir * (0.5 * start_buff)
                    ]))
                if end_buff < 0:
                    extra_points.append(np.array([
                        points[-1] - end_dir * (0.5 * end_buff),
                        points[-1] - end_dir * end_buff
                    ]))
                points = np.vstack(extra_points)

        return points

    @staticmethod
    def pointify_start_and_end(
        start: Cmpt_Points.BoundingBox | Vect,
        end: Cmpt_Points.BoundingBox | Vect
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        将起点与终点输入解析为用于构造线段的三维坐标对

        先基于两者的粗略位置计算方向向量，再在输入为边界框时沿该方向提取边界点，从而得到更符合连接方向的首尾点

        :param start: 起点，可为边界框对象或坐标
        :param end: 终点，可为边界框对象或坐标
        :return: 解析后的 ``(start, end)`` 三维坐标
        """
        # 首先得到 start 和 end 之间的指向
        rough_start, rough_end = Line.pointify(start), Line.pointify(end)
        if np.isclose(rough_start, rough_end).all():
            rough_end[0] += 1e-6
        vect = normalize(rough_end - rough_start)

        # 在是物件的情况下，接着会通过得出的指向细化位于物件边界框上的位置
        return (Line.pointify(start, vect), Line.pointify(end, -vect))

    @staticmethod
    def pointify(
        input: Cmpt_Points.BoundingBox | Vect,
        direction: Vect | None = None
    ) -> np.ndarray:
        """
        将输入解析为三维坐标点

        若传入为边界框对象，未给定方向时返回中心点，给定方向时返回该方向上的边界点；若传入坐标序列，则补齐到 3 维后返回

        :param input: 边界框对象或坐标
        :param direction: 用于提取物件坐标，默认为 ``None`` 提取其中心点，或是指定一个方向提取其边界框上指定方向的点（使用 :meth:`~.BoundingBox.get_continuous` ）
        :return: 解析得到的三维坐标
        """
        if isinstance(input, Cmpt_Points.BoundingBox):
            box = input
            if direction is None:
                return box.center
            else:
                return box.get_continuous(direction)
        else:
            point = input
            result = np.zeros(3)
            result[:len(point)] = point
            return result

    # endregion


class Cmpt_VPoints_DashedLineImpl[ItemT](Cmpt_VPoints_LineImpl[ItemT], impl=True):
    """
    在虚线中，对 :class:`~.Cmpt_VPoints` 的进一步实现
    """
    def get_start(self) -> np.ndarray:
        assert self.bind is not None
        sub = self.bind.at_item._children[0]
        assert isinstance(sub, VItem)
        return sub.points.get_start()

    def get_end(self) -> np.ndarray:
        assert self.bind is not None
        sub = self.bind.at_item._children[-1]
        assert isinstance(sub, VItem)
        return sub.points.get_end()


class DashedLine(Line, Group[VItem]):
    """
    虚线

    :param dash_length: 每段虚线的长度
    :param dashed_ratio: 虚线段的占比，默认为 ``0.5``，即虚线段与空白段长度相等，但可能因为虚线段描边存在粗细而导致视觉上空白长度略小
    :param strict_by_length: 虚线段长度是否严格遵从 ``dash_length``，默认为 ``False``

        - 当为 ``False`` 时，可能会微调以确保首尾都是完整的虚线段
        - 当为 ``True`` 时，不再微调，但是尾部虚线段可能不完整

        在静态使用的情境下，使用 ``False`` 会更美观；在动态创建的情境下，使用 ``True`` 可以避免频繁抖动

    :param \\*\\*kwargs: 其它参数，另见 :class:`Line`

    .. warning::

        由于一些因素，:class:`~.DashedLine` 并不完全具有 :class:`~.Line` 的功能

        这是由于 :class:`~.DashedLine` 实际上将每段虚线作为子物件来实现，而去除了自己本身的 ``points`` 数据，
        这会导致包括 ``.reshape`` 以及 ``.points.vector`` 等一些方法不可用
    """
    def __init__(
        self,
        start: Vect | Points = LEFT,
        end: Vect | Points = RIGHT,
        *,
        dash_length: float = DEFAULT_DASH_LENGTH,
        dashed_ratio: float = 0.5,
        strict_by_length: bool = False,
        **kwargs
    ) -> None:
        self.dash_length = dash_length
        self.dashed_ratio = dashed_ratio
        super().__init__(start, end, **kwargs)
        if not strict_by_length:
            dashes = DashedVItem(
                self,
                num_dashes=self._calculate_num_dashes(),
                dashed_ratio=dashed_ratio,
            )
        else:
            dashes = DashedVItemByRatio(
                self,
                dash_ratio=self._calculate_dash_ratio(),
                dashed_ratio=dashed_ratio
            )
        self.points.clear()
        self.add(*dashes)

    def _calculate_num_dashes(self) -> int:
        """
        基于线段长度计算所需虚线段的数量
        """
        return max(
            2,
            int(np.ceil((self.points.arc_length / self.dash_length) * self.dashed_ratio)),
        )

    def _calculate_dash_ratio(self) -> float:
        """
        基于线段长度计算每段虚线段占总长的比率
        """
        # max 1e-5 避免除零
        return self.dash_length / max(1e-5, self.points.arc_length)


class TangentLine(Line):
    """
    切线

    - 传入 ``vitem`` 表示需要做切线的物件，``alpha`` 表示切点在 ``vitem`` 上的比例
    - ``length``: 切线长度
    - ``d_alpha``: 精细程度，越小越精细（默认 ``1e-6``）
    """
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
    """
    折线（一般用作直角符号），关于直接基于两条线创建的直角符号，另请参见 :class:`~.RightAngle`

    :param width: 直角标记的边长
    :param angle: 起始角度
    """
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
    """
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
    """
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
        """
        返回一个包含构成该角的两个 :class:`~.Line` 的 :class:`~.Group` 对象
        """
        return Group(*self.lines)

    def get_value(self, degrees: bool = False) -> float:
        """
        获取该角的数值

        - ``degrees``: 是否以角度的形式返回，默认为 ``False``，即弧度制
        """
        return self.angle_value / DEGREES if degrees else self.angle_value

    @staticmethod
    def from_three_points(
        A: Vect, B: Vect, C: Vect, **kwargs
    ) -> Angle:
        """
        由三点构造一个角，表示 ∠ABC，点 ``B`` 为角的顶点
        """
        return Angle(Line(B, A), Line(B, C), **kwargs)


class RightAngle(Angle):
    """
    一个用于表示直角的 :class:`Elbow` 样式的对象（L 形折角）

    - ``length``: 直角标记的边长
    """
    def __init__(
        self,
        line1: Line,
        line2: Line,
        length: float | None = None,
        **kwargs,
    ) -> None:
        super().__init__(line1, line2, radius=length, elbow=True, **kwargs)


# TODO: CubicBezier
