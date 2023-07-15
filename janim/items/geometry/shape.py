from __future__ import annotations

from janim.constants import *
from janim.items.vitem import VItem
from janim.items.geometry.arc import ArcBetweenPoints
from janim.items.geometry.line import Line
from janim.utils.iterables import adjacent_n_tuples
from janim.utils.space_ops import (
    normalize, angle_between_vectors,
    adjacent_pairs
)


class Polygon(VItem):
    def __init__(
        self, 
        *verts: np.ndarray, 
        close_path: bool = True, 
        **kwargs
    ):
        self.vertices = verts
        super().__init__(**kwargs)
        self.set_points_as_corners(
            [*verts, verts[0]]
            if close_path
            else verts
        )    

    def get_vertices(self) -> list[np.ndarray]:
        return self.get_start_points()

    def round_corners(self, radius: float = 0.5):
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
