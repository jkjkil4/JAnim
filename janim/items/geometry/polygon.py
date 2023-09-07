from __future__ import annotations
from typing import Optional, overload
from janim.typing import Self

from janim.constants import *
from janim.items.vitem import VItem
from janim.items.geometry.arc import ArcBetweenPoints
from janim.items.geometry.line import Line
from janim.utils.iterables import adjacent_n_tuples
from janim.utils.space_ops import (
    normalize, angle_between_vectors,
    adjacent_pairs, rotate_vector,
    compass_directions
)


class Polygon(VItem):
    def __init__(
        self, 
        *verts: np.ndarray, 
        close_path: bool = True, 
        **kwargs
    ) -> None:
        self.vertices = verts
        super().__init__(**kwargs)
        self.set_points_as_corners(
            [*verts, verts[0]]
            if close_path
            else verts
        )    

    def get_vertices(self) -> list[np.ndarray]:
        return self.get_start_points()

    def round_corners(self, radius: float = 0.5) -> Self:
        vertices = self.get_vertices()
        arcs = []
        for v1, v2, v3 in adjacent_n_tuples(vertices, 3):
            vect1 = v2 - v1
            vect2 = v3 - v2
            unit_vect1 = normalize(vect1)
            unit_vect2 = normalize(vect2)
            angle = angle_between_vectors(vect1, vect2)
            # Negative radius gives concave curves
            angle *= np.sign(radius)
            # Distance between vertex and start of the arc
            cut_off_length = radius * np.tan(angle / 2)
            # Determines counterclockwise vs. clockwise
            sign = np.sign(np.cross(vect1, vect2)[2])
            arc = ArcBetweenPoints(
                v2 - unit_vect1 * cut_off_length,
                v2 + unit_vect2 * cut_off_length,
                angle=sign * angle,
                n_components=2,
            )
            arcs.append(arc)

        self.clear_points()
        # To ensure that we loop through starting with last
        arcs: list[ArcBetweenPoints] = [arcs[-1], *arcs[:-1]]
        for arc1, arc2 in adjacent_pairs(arcs):
            self.append_points(arc1.get_points())
            line = Line(arc1.get_end(), arc2.get_start())
            # Make sure anchors are evenly distributed
            len_ratio = line.get_length() / arc1.get_arc_length()
            line.insert_n_curves(
                int(arc1.curves_count() * len_ratio)
            )
            self.append_points(line.get_points())
        return self
    
class Polyline(Polygon):
    def __init__(
        self, 
        *verts: np.ndarray, 
        close_path: bool = False, 
        **kwargs
    ) -> None:
        super().__init__(*verts, close_path=close_path, **kwargs)

class RegularPolygon(Polygon):
    def __init__(
        self,
        n: int = 6,
        start_angle: Optional[float] = None,
        **kwargs
    ) -> None:
        if start_angle is None:
            start_angle = (n % 2) * PI / 2
        start_vect = rotate_vector(RIGHT, start_angle)
        vertices = compass_directions(n, start_vect)
        super().__init__(*vertices, **kwargs)

class Triangle(RegularPolygon):
    def __init__(self, **kwargs):
        super().__init__(n=3, **kwargs)

class Rectangle(Polygon):
    @overload
    def __init__(self, width: float = 4.0, height: float = 2.0, **kwargs) -> None: ...
    @overload
    def __init__(self, corner1: Iterable, corner2: Iterable, **kwargs) -> None: ...

    def __init__(self, v1, v2, **kwargs) -> None:
        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            super().__init__(UR, UL, DL, DR, **kwargs)
            self.set_size(v1, v2)
        
        elif isinstance(v1, Iterable) and isinstance(v2, Iterable):
            ul = np.array([min(v1, v2) for v1, v2 in zip(v1, v2)])
            dr = np.array([max(v1, v2) for v1, v2 in zip(v1, v2)])
            super().__init__(UR, UL, DL, DR, **kwargs)
            self.set_size(*(dr - ul)[:2])
            self.move_to((dr + ul) / 2)
        
        else:
            raise TypeError('Called with wrong argument types')

class Square(Rectangle):
    def __init__(self, side_length: float = 2.0, **kwargs) -> None:
        self.side_length = side_length
        super().__init__(side_length, side_length, **kwargs)

class RoundedRectangle(Rectangle):
    def __init__(
        self, 
        corner_radius: float = 0.5,
        **kwargs
    ) -> None:
        Rectangle.__init__(self, **kwargs)
        self.round_corners(corner_radius)
