
from typing import Iterable, overload

import numpy as np

from janim.constants import DL, DR, PI, RIGHT, UL, UR
from janim.items.vitem import VItem
from janim.typing import Vect, VectArray
from janim.utils.space_ops import compass_directions, rotate_vector


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
        return self.points.get()[::2]

    # TODO: round_corners


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


class RegularPolygon(Polygon):
    '''正多边形

    传入数字 ``n`` 表示边数
    '''
    def __init__(
        self,
        n: int = 6,
        *,
        start_angle: float | None = None,
        **kwargs
    ):
        if start_angle is None:
            start_angle = (n % 2) * PI / 2
        start_vect = rotate_vector(RIGHT, start_angle)
        vertices = compass_directions(n, start_vect)
        super().__init__(*vertices, **kwargs)


class Triangle(RegularPolygon):
    '''
    正三角形
    '''
    def __init__(self, **kwargs):
        super().__init__(n=3, **kwargs)


class Rectangle(Polygon):
    '''矩形

    - 可以使用 ``Rectangle(4, 2)`` 的传入宽高的方式进行构建
    - 也可以使用 ``Rectangle(p1, p2)`` 的传入对角顶点的方式进行构建
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


class Square(Rectangle):
    '''正方形

    ``side_length`` 表示正方形边长
    '''
    def __init__(self, side_length: float = 2.0, **kwargs) -> None:
        self.side_length = side_length
        super().__init__(side_length, side_length, **kwargs)


# TODO: RoundedRectangle
