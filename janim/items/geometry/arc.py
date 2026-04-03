
from typing import Self

import numpy as np

from janim.components.component import CmptInfo
from janim.components.vpoints import Cmpt_VPoints
from janim.constants import LEFT, MED_SMALL_BUFF, NAN_POINT, ORIGIN, RIGHT, TAU
from janim.items.geometry import GeometryShape
from janim.items.item import Item
from janim.items.points import MarkedItem
from janim.items.vitem import VItem
from janim.typing import Alpha, AlphaArray, Vect
from janim.utils.bezier import PathBuilder, quadratic_bezier_points_for_arc
from janim.utils.space_ops import (angle_between_vectors, angle_of_vector,
                                   get_norm)

DEFAULT_DOT_RADIUS = 0.08
DEFAULT_SMALL_DOT_RADIUS = 0.04


class ArcCenter(MarkedItem, VItem):
    """
    与圆弧有关的类的基类，被 :class:`Arc` 和 :class:`AnnularSector` 所继承
    """
    def __init__(self, *args, arc_center: Vect = ORIGIN, **kwargs):
        super().__init__(*args, **kwargs)

        self.mark.set_points([arc_center])

    def get_arc_center(self) -> np.ndarray:
        """得到圆弧所对应的圆心"""
        return self.mark.get()

    def move_arc_center_to(self, point: Vect) -> Self:
        """将圆弧圆心移动到指定的位置"""
        self.mark.set(point)
        return self


class Arc(GeometryShape, ArcCenter):
    """
    圆弧

    - ``start_angle`` 表示起始的角度
    - ``angle`` 表示圆心角
    """
    def __init__(
        self,
        start_angle: float = 0,
        angle: float = TAU / 4,
        radius: float = 1.0,
        *,
        n_components: int = 8,
        arc_center: np.ndarray = ORIGIN,
        **kwargs
    ) -> None:
        super().__init__(arc_center=arc_center, **kwargs)
        self._reshape(start_angle, angle, radius, n_components, arc_center)

    # region reshape

    def _reshape(
        self,
        start_angle: float | None = None,
        angle: float | None = None,
        radius: float | None = None,
        n_components: int | None = None,
        arc_center: Vect | None = None
    ) -> None:
        start_angle, angle, radius, n_components = \
            self._reshape_memorize(start_angle=start_angle, angle=angle, radius=radius, n_components=n_components)

        if arc_center is None:
            arc_center = self.mark.get()

        self.points.set(
            quadratic_bezier_points_for_arc(
                angle=angle,
                start_angle=start_angle,
                n_components=n_components
            ) * radius + arc_center
        )

    def reshape(
        self,
        start_angle: float | None = None,
        angle: float | None = None,
        radius: float | None = None,
        *,
        n_components: int | None = None,
        arc_center: Vect | None = None
    ) -> Self:
        self._reshape(start_angle, angle, radius, n_components, arc_center)
        if arc_center is not None:
            self.mark.set_points([arc_center])
        return self

    # endregion

    def get_arc_length(self) -> float:
        """获取圆弧长度"""
        center = self.get_arc_center()
        p0 = self.points.get_start()
        p1 = self.points.pfp(0.5)
        vc0 = p0 - center
        vc1 = p1 - center

        return 2 * get_norm(vc0) * angle_between_vectors(vc0, vc1)

    def get_start_angle(self) -> float:
        """获取起始角度"""
        angle = angle_of_vector(self.points.get_start() - self.get_arc_center())
        return angle % TAU

    def get_stop_angle(self) -> float:
        """获取终止角度"""
        angle = angle_of_vector(self.points.get_end() - self.get_arc_center())
        return angle % TAU


class ArcBetweenPoints(Arc):
    """
    两点之间的圆弧

    - 传入 ``start``, ``end`` 表示起点终点
    - ``angle`` 表示圆心角
    - 其余参数同 :class:`Arc`
    """
    def __init__(
        self,
        start: np.ndarray,
        end: np.ndarray,
        angle: float = TAU / 4,
        **kwargs
    ) -> None:
        super().__init__(angle=angle, **kwargs)
        self._reshape_start_and_end(start, end)

    # region reshape

    def reshape(
        self,
        start: Vect | None = None,
        end: Vect | None = None,
        *,
        angle: float | None = None
    ) -> Self:
        super().reshape(angle=angle)
        self._reshape_start_and_end(start, end)
        return self

    def _reshape_start_and_end(self, start: Vect | None = None, end: Vect | None = None) -> None:
        start, end = self._reshape_memorize(start=start, end=end)
        angle = self.reshape_params['angle']
        if angle == 0:
            self.points.set_as_corners([LEFT, RIGHT])
        self.points.put_start_and_end_on(start, end)

    # endregion


class Cmpt_VPoints_CircleImpl[ItemT](Cmpt_VPoints[ItemT], impl=True):
    """
    在圆中，对 :class:`~.Cmpt_VPoints` 的进一步实现
    """
    def surround(
        self,
        item: Item,
        dim_to_match: int = 0,
        *,
        stretch: bool = False,
        buff: float = MED_SMALL_BUFF,
        root_only: bool = True,
        item_root_only: bool = False,
    ) -> Self:
        # Ignores dim_to_match and stretch; result will always be a circle
        # REFACTOR:  Perhaps create an ellipse class to handle singele-dimension stretching
        self.replace(item, dim_to_match, stretch=stretch, root_only=root_only, item_root_only=item_root_only)
        self.set_size(self.box.width + 2 * buff, self.box.height + 2 * buff)
        return self

    @property
    def start_angle(self) -> float:
        """获取起始角度"""
        angle = angle_of_vector(self.get_start() - self.box.center)
        return angle % TAU

    def at_angle(self, angle: float) -> np.ndarray:
        """
        得到在指定角度处的点，例如 ``angle=0`` 得到右侧的点，``angle=PI / 2`` 得到顶部的点
        """
        return self.pfp(
            (angle - self.start_angle) / TAU % 1
        )

    @property
    def radius(self) -> float:
        """得到半径"""
        return get_norm(self.get_start() - self.box.center)


class Circle(GeometryShape):
    """
    圆

    - 参数同 :class:`Arc`
    - 半径传入 ``radius`` 指定
    """
    points = CmptInfo(Cmpt_VPoints_CircleImpl[Self])

    def __init__(
        self,
        radius: float = 1.0,
        *,
        n_components: int = 8,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._reshape(radius=radius, n_components=n_components)

    # region reshape

    def _reshape(self, radius: float | None = None, n_components: int | None = None) -> None:
        radius, n_components = self._reshape_memorize(radius=radius, n_components=n_components)

        self.points.set(
            quadratic_bezier_points_for_arc(
                angle=TAU,
                start_angle=0,
                n_components=n_components
            ) * radius
        )

    def reshape(self, radius: float | None = None, *, n_components: int | None = None) -> Self:
        center = self.points.box.center
        self._reshape(radius=radius, n_components=n_components)
        self.points.shift(center)
        return self

    # endregion


class Dot(Circle):
    """
    点，半径默认为 ``0.08``
    """
    def __init__(
        self,
        point: np.ndarray = ORIGIN,
        radius: float = DEFAULT_DOT_RADIUS,
        *,
        stroke_alpha: Alpha | AlphaArray | None = 0,
        fill_alpha: Alpha | AlphaArray | None = 1.0,
        **kwargs
    ) -> None:
        super().__init__(
            radius=radius,
            stroke_alpha=stroke_alpha,
            fill_alpha=fill_alpha,
            **kwargs
        )
        self.points.move_to(point)


class SmallDot(Dot):
    """
    小点，半径默认为 ``0.04``
    """
    def __init__(self, point: np.ndarray = ORIGIN, radius: float = DEFAULT_SMALL_DOT_RADIUS, **kwargs) -> None:
        super().__init__(point, radius, **kwargs)


class Ellipse(Circle):
    """
    椭圆
    """
    def __init__(
        self,
        width: float = 2,
        height: float = 1,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self._reshape_size(width, height)

    # region reshape

    def reshape(self, width: float | None = None, height: float | None = None) -> Self:
        self._reshape_size(width, height)
        return self

    def _reshape_size(self, width: float | None = None, height: float | None = None) -> Self:
        width, height = self._reshape_memorize(width=width, height=height)
        self.points.set_size(width, height)

    # endregion


class AnnularSector(GeometryShape, ArcCenter):
    """
    扇环

    - ``inner_radius``: 内圆半径
    - ``outer_radius``: 外圆半径
    - ``start_angle``: 起始角度
    - ``angle``: 圆心角
    - ``arc_center``: 圆弧的中心
    """
    def __init__(
        self,
        inner_radius: float = 0.5,
        outer_radius: float = 1,
        start_angle: float = 0,
        angle: float = TAU / 4,
        *,
        arc_center: np.ndarray = ORIGIN,
        n_components: int = 8,
        **kwargs
    ) -> None:
        super().__init__(arc_center=arc_center, **kwargs)
        self._reshape(inner_radius, outer_radius, start_angle, angle, n_components, arc_center)

    # region reshape

    def _reshape(
        self,
        inner_radius: float | None = None,
        outer_radius: float | None = None,
        start_angle: float | None = None,
        angle: float | None = None,
        n_components: int | None = None,
        arc_center: Vect | None = None,
    ) -> None:
        # 参数记忆逻辑
        inner_radius, outer_radius, start_angle, angle, n_components = self._reshape_memorize(
            inner_radius=inner_radius,
            outer_radius=outer_radius,
            start_angle=start_angle,
            angle=angle,
            n_components=n_components,
        )

        if arc_center is None:
            arc_center = self.mark.get()

        # 真正处理
        unit = quadratic_bezier_points_for_arc(
            angle=angle,
            start_angle=start_angle,
            n_components=n_components
        )

        inner_arc, outer_arc = (
            unit * radius
            for radius in (inner_radius, outer_radius)
        )
        inner_arc = inner_arc[::-1]

        builder = PathBuilder(points=outer_arc)
        builder.append(inner_arc, line_to_start_point=True).close_path()

        self.points.set(builder.get() + arc_center)

    def reshape(
        self,
        inner_radius: float | None = None,
        outer_radius: float | None = None,
        start_angle: float | None = None,
        angle: float | None = None,
        *,
        arc_center: Vect | None = None,
        n_components: int | None = None,
    ) -> Self:
        self._reshape(inner_radius, outer_radius, start_angle, angle, n_components, arc_center)
        if arc_center is not None:
            self.mark.set_points([arc_center])
        return self

    # endregion


class Sector(Arc):
    """
    扇形

    传入参数请参考 :class:`Arc`
    """
    def __init__(self, *, arc_center: np.ndarray = ORIGIN, **kwargs) -> None:
        super().__init__(arc_center=arc_center, **kwargs)
        self._reshape_additional_corners()

    # region reshape

    def reshape(
        self,
        start_angle: float | None = None,
        angle: float | None = None,
        radius: float | None = None,
        *,
        n_components: int | None = None,
        arc_center: Vect | None = None
    ) -> Self:
        super().reshape(start_angle, angle, radius, n_components=n_components, arc_center=arc_center)
        self._reshape_additional_corners()
        return self

    def _reshape_additional_corners(self) -> None:
        self.points.add_as_corners([self.get_arc_center(), self.points.get_start()])

    # endregion


class Annulus(GeometryShape):
    """
    圆环

    - ``inner_radius``: 内圆半径
    - ``outer_radius``: 外圆半径
    - ``arc_center``: 圆弧的中心
    """
    def __init__(
        self,
        outer_radius: float = 1,
        inner_radius: float = 0.5,
        *,
        arc_center: np.ndarray = ORIGIN,
        n_components: int = 8,
        fill_alpha: float = 0.5,
        **kwargs
    ) -> None:
        super().__init__(fill_alpha=fill_alpha, **kwargs)
        self._reshape(arc_center, outer_radius, inner_radius, n_components)

    # region reshape

    def _reshape(
        self,
        arc_center: Vect,
        outer_radius: float | None = None,
        inner_radius: float | None = None,
        n_components: int | None = None,
    ) -> None:
        outer_radius, inner_radius, n_components = self._reshape_memorize(
            outer_radius=outer_radius,
            inner_radius=inner_radius,
            n_components=n_components
        )
        arc_center = np.array(arc_center)

        unit = quadratic_bezier_points_for_arc(
            TAU, 0,
            n_components
        )

        inner, outer = (
            unit * radius + arc_center
            for radius in (inner_radius, outer_radius)
        )
        outer = outer[::-1]

        self.points.set(np.vstack([outer, NAN_POINT, inner]))

    def reshape(
        self,
        outer_radius: float | None = None,
        inner_radius: float | None = None,
        *,
        arc_center: Vect | None = None,
        n_components: int | None = None,
    ) -> Self:
        if arc_center is None:
            arc_center = self.points.box.center
        self._reshape(arc_center, outer_radius, inner_radius, n_components)
        return self

    # endregion
