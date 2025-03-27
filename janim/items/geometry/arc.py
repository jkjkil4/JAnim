
from typing import Self

import numpy as np

from janim.components.component import CmptInfo
from janim.components.vpoints import Cmpt_VPoints
from janim.constants import LEFT, MED_SMALL_BUFF, NAN_POINT, ORIGIN, RIGHT, TAU
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
    '''
    与圆弧有关的类的基类，被 :class:`Arc` 和 :class:`AnnularSector` 所继承
    '''
    def __init__(self, *args, arc_center: Vect = ORIGIN, **kwargs):
        super().__init__(*args, **kwargs)

        self.mark.set_points([arc_center])

    def get_arc_center(self) -> np.ndarray:
        '''得到圆弧所对应的圆心'''
        return self.mark.get()

    def move_arc_center_to(self, point: Vect) -> Self:
        '''将圆弧圆心移动到指定的位置'''
        self.mark.set(point)
        return self


class Arc(ArcCenter):
    '''
    圆弧

    - ``start_angle`` 表示起始的角度
    - ``angle`` 表示圆心角
    '''
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

        self.points.set(
            quadratic_bezier_points_for_arc(
                angle=angle,
                start_angle=start_angle,
                n_components=n_components
            ) * radius + arc_center
        )

    def get_arc_length(self) -> float:
        '''获取圆弧长度'''
        center = self.get_arc_center()
        p0 = self.points.get_start()
        p1 = self.points.pfp(0.5)
        vc0 = p0 - center
        vc1 = p1 - center

        return 2 * get_norm(vc0) * angle_between_vectors(vc0, vc1)

    def get_start_angle(self) -> float:
        '''获取起始角度'''
        angle = angle_of_vector(self.points.get_start() - self.get_arc_center())
        return angle % TAU

    def get_stop_angle(self) -> float:
        '''获取终止角度'''
        angle = angle_of_vector(self.points.get_end() - self.get_arc_center())
        return angle % TAU


class ArcBetweenPoints(Arc):
    '''
    两点之间的圆弧

    - 传入 ``start``, ``end`` 表示起点终点
    - ``angle`` 表示圆心角
    - 其余参数同 ``Arc``
    '''
    def __init__(
        self,
        start: np.ndarray,
        end: np.ndarray,
        angle: float = TAU / 4,
        **kwargs
    ) -> None:
        super().__init__(angle=angle, **kwargs)
        if angle == 0:
            self.points.set_as_corners([LEFT, RIGHT])
        self.points.put_start_and_end_on(start, end)


class Cmpt_VPoints_CircleImpl[ItemT](Cmpt_VPoints[ItemT], impl=True):
    '''
    在圆中，对 :class:`~.Cmpt_VPoints` 的进一步实现
    '''
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
        '''获取起始角度'''
        angle = angle_of_vector(self.get_start() - self.box.center)
        return angle % TAU

    def at_angle(self, angle: float) -> np.ndarray:
        '''
        得到在指定角度处的点，例如 ``angle=0`` 得到右侧的点，``angle=PI / 2`` 得到顶部的点
        '''
        return self.pfp(
            (angle - self.start_angle) / TAU % 1
        )

    @property
    def radius(self) -> float:
        '''得到半径'''
        return get_norm(self.get_start() - self.box.center)


class Circle(VItem):
    '''
    圆

    - 参数同 ``Arc``
    - 半径传入 ``radius`` 指定
    '''
    points = CmptInfo(Cmpt_VPoints_CircleImpl[Self])

    def __init__(
        self,
        radius: float = 1.0,
        *,
        n_components: int = 8,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.points.set(
            quadratic_bezier_points_for_arc(
                angle=TAU,
                start_angle=0,
                n_components=n_components
            ) * radius
        )


class Dot(Circle):
    '''
    点，半径默认为 ``0.08``
    '''
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
    '''
    小点，半径默认为 ``0.04``
    '''
    def __init__(self, point: np.ndarray = ORIGIN, radius: float = DEFAULT_SMALL_DOT_RADIUS, **kwargs) -> None:
        super().__init__(point, radius, **kwargs)


class Ellipse(Circle):
    '''
    椭圆
    '''
    def __init__(
        self,
        width: float = 2,
        height: float = 1,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.points.set_size(width, height)


class AnnularSector(ArcCenter):
    '''
    扇环

    - ``inner_radius``: 内圆半径
    - ``outer_radius``: 外圆半径
    - ``start_angle``: 起始角度
    - ``angle``: 圆心角
    - ``arc_center``: 圆弧的中心
    '''
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

        unit = quadratic_bezier_points_for_arc(
            angle=angle,
            start_angle=start_angle,
            n_components=n_components
        )

        inner_arc, outer_arc = (
            unit * radius + arc_center
            for radius in (inner_radius, outer_radius)
        )
        inner_arc = inner_arc[::-1]

        builder = PathBuilder(points=outer_arc)
        builder.append(inner_arc, line_to_start_point=True).close_path()

        self.points.set(builder.get() + arc_center)


class Sector(Arc):
    '''
    扇形

    传入参数请参考 ``Arc``
    '''
    def __init__(self, *, arc_center: np.ndarray = ORIGIN, **kwargs) -> None:
        super().__init__(arc_center=arc_center, **kwargs)

        self.points.add_as_corners([arc_center, self.points.get_start()])


class Annulus(VItem):
    '''
    圆环

    - ``inner_radius``: 内圆半径
    - ``outer_radius``: 外圆半径
    - ``arc_center``: 圆弧的中心
    '''
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
