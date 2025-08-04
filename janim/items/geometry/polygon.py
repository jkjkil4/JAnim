
import itertools as it
from typing import Iterable, Self, overload

import numpy as np

from janim.constants import DL, DR, ORIGIN, PI, RIGHT, TAU, UL, UR
from janim.items.geometry.arc import ArcBetweenPoints
from janim.items.points import MarkedItem
from janim.items.vitem import VItem
from janim.locale.i18n import get_local_strings
from janim.typing import Vect, VectArray
from janim.utils.bezier import PathBuilder
from janim.utils.iterables import adjacent_n_tuples
from janim.utils.space_ops import (angle_between_vectors, compass_directions,
                                   cross2d, get_norm, normalize, rotate_vector)

_ = get_local_strings('polygon')


class Polygon(VItem):
    '''
    多边形

    传入顶点列表 ``verts`` 进行表示
    '''
    def __init__(
        self,
        *verts: VectArray,
        close_path: bool = True,
        **kwargs
    ):
        self.vertices = verts
        super().__init__(**kwargs)
        self.points.set_as_corners(
            [*verts, verts[0]]
            if close_path
            else verts
        )

    def get_vertices(self) -> list[np.ndarray]:
        return self.points.get()[:-1:2]

    def round_corners(self, radius: float | None = None) -> Self:
        verts = self.get_vertices()
        min_edge_length = min(
            get_norm(v1 - v2)
            for v1, v2 in zip(verts, verts[1:])
            if not np.isclose(v1, v2).all()
        )
        if radius is None:
            radius = 0.25 * min_edge_length
        else:
            radius = min(radius, 0.5 * min_edge_length)
        vertices = self.get_vertices()
        arcs: list[ArcBetweenPoints] = []

        for v1, v2, v3 in adjacent_n_tuples(vertices, 3):
            vect1 = normalize(v2 - v1)
            vect2 = normalize(v3 - v2)
            angle = angle_between_vectors(vect1, vect2)
            # Distance between vertex and start of the arc
            cut_off_length = radius * np.tan(angle / 2)
            # Negative radius gives concave curves
            sign = float(np.sign(radius * cross2d(vect1, vect2)))
            arc = ArcBetweenPoints(
                v2 - vect1 * cut_off_length,
                v2 + vect2 * cut_off_length,
                angle=sign * angle,
                n_components=2,
            )
            arcs.append(arc)

        builder = PathBuilder(start_point=arcs[-1].points.get_end())
        for arc in arcs:
            if not np.isclose(builder.end_point, arc.points.get_start()).all():
                builder.line_to(arc.points.get_start())
            builder.append(arc.points.get()[1:])
        self.points.set(builder.get())
        return self


class Polyline(Polygon):
    '''多边形折线

    与 :class:`Polygon` 的区别是，不会自动将最后一个点与第一个点连接
    '''
    def __init__(
        self,
        *verts: VectArray,
        close_path: bool = False,
        **kwargs
    ):
        super().__init__(*verts, close_path=close_path, **kwargs)


class RegularPolygon(MarkedItem, Polygon):
    '''正多边形

    传入数字 ``n`` 表示边数

    可通过 ``.mark.get()`` 得到多边形的中心
    '''
    def __init__(
        self,
        n: int = 6,
        *,
        radius: float = 1,
        start_angle: float | None = None,
        **kwargs
    ):
        if start_angle is None:
            start_angle = (n % 2) * PI / 2
        start_vect = rotate_vector(RIGHT * radius, start_angle)
        vertices = compass_directions(n, start_vect)
        super().__init__(*vertices, **kwargs)

        self.mark.set_points([ORIGIN])


class Triangle(RegularPolygon):
    '''
    正三角形
    '''
    def __init__(self, **kwargs):
        super().__init__(n=3, **kwargs)


class Rect(Polygon):
    '''矩形

    - 可以使用 ``Rect(4, 2)`` 的传入宽高的方式进行构建
    - 也可以使用 ``Rect(p1, p2)`` 的传入对角顶点的方式进行构建
    '''
    @overload
    def __init__(self, width: float = 4.0, height: float = 2.0, /, **kwargs) -> None: ...
    @overload
    def __init__(self, corner1: Vect, corner2: Vect, /, **kwargs) -> None: ...

    def __init__(self, v1=4.0, v2=2.0, /, **kwargs) -> None:
        if isinstance(v1, Iterable) and isinstance(v2, Iterable):
            ul = np.array([min(v1, v2) for v1, v2 in zip(v1, v2)])
            dr = np.array([max(v1, v2) for v1, v2 in zip(v1, v2)])
            super().__init__(UR, UL, DL, DR, **kwargs)
            self.points.set_size(*(dr - ul)[:2])
            self.points.move_to((dr + ul) / 2)

        else:
            super().__init__(UR, UL, DL, DR, **kwargs)
            self.points.set_size(v1, v2)


class Square(Rect):
    '''正方形

    ``side_length`` 表示正方形边长
    '''
    def __init__(self, side_length: float = 2.0, **kwargs) -> None:
        self.side_length = side_length
        super().__init__(side_length, side_length, **kwargs)


class RoundedRect(Rect):
    '''圆角矩形'''
    @overload
    def __init__(self, width: float = 4.0, height: float = 2.0, /, corner_radius: float = 0.5, **kwargs) -> None: ...
    @overload
    def __init__(self, corner1: Vect, corner2: Vect, /, corner_radius: float = 0.5, **kwargs) -> None: ...

    def __init__(self, v1=4.0, v2=2.0, /, corner_radius: float = 0.5, **kwargs) -> None:
        super().__init__(v1, v2, **kwargs)
        self.round_corners(corner_radius)


class Star(MarkedItem, Polygon):
    '''
    星形

    - ``n`` 表示顶点数，默认为 5
    - ``outer_radius`` 表示外半径
    - ``inner_radius`` 表示内半径，默认为 ``None``，由 ``density`` 决定
    - ``density`` 表示密度，数值越高，内半径越小，取值范围 ``[1, n/2]``
    - ``start_angle`` 表示起始角度，即星形的旋转角度
    '''
    def __init__(
        self,
        n: int = 5,
        *,
        outer_radius: float = 1,
        inner_radius: float | None = None,
        density: int = 2,
        start_angle: float | None = TAU / 4,
        **kwargs
    ):
        inner_angle = TAU / (2 * n)

        if inner_radius is None:
            # See https://math.stackexchange.com/a/2136292 for an
            # overview of how to calculate the inner radius of a
            # perfect star.

            if density <= 0 or density >= n / 2:
                raise ValueError(
                    _('Incompatible density {density} for number of points {n}')
                    .format(density=density, n=n),
                )

            outer_angle = TAU * density / n
            inverse_x = 1 - np.tan(inner_angle) * (
                (np.cos(outer_angle) - 1) / np.sin(outer_angle)
            )

            inner_radius = outer_radius / (np.cos(inner_angle) * inverse_x)

        start_vect = rotate_vector(RIGHT * outer_radius, start_angle)
        outer_vertices = compass_directions(n, start_vect)

        start_vect = rotate_vector(RIGHT * inner_radius, start_angle + inner_angle)
        inner_vertices = compass_directions(n, start_vect)

        super().__init__(*it.chain.from_iterable(zip(outer_vertices, inner_vertices)), **kwargs)
        self.start_angle = start_angle

        self.mark.set_points([ORIGIN])
