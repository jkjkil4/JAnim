from __future__ import annotations
from typing import Iterable, Optional
from janim.typing import Self

from janim.constants import *
from janim.items.item import Item
from janim.items.vitem import VItem
from janim.items.geometry.arc import Arc
from janim.utils.space_ops import (
    get_norm, normalize,
    rotate_vector, angle_of_vector
)

class Line(VItem):
    def __init__(
        self,
        start: np.ndarray = LEFT,
        end: np.ndarray = RIGHT,
        buff: float = 0,
        path_arc: float = 0,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.start = start
        self.end = end
        self.buff = buff
        self.path_arc = path_arc

        self.set_points_by_ends(start, end, buff, path_arc)
    
    def set_points_by_ends(
        self,
        start: np.ndarray,
        end: np.ndarray,
        buff: float = 0,
        path_arc: float = 0
    ) -> Self:
        vect = end - start
        dist = get_norm(vect)
        if np.isclose(dist, 0):
            self.set_points_as_corners([start, end])
            return self
        if path_arc:
            neg = path_arc < 0
            if neg:
                path_arc = -path_arc
                start, end = end, start
            radius = (dist / 2) / np.sin(path_arc / 2)
            alpha = (PI - path_arc) / 2
            center = start + radius * normalize(rotate_vector(end - start, alpha))

            raw_arc_points = Arc.create_quadratic_bezier_points(
                angle=path_arc - 2 * buff / radius,
                start_angle=angle_of_vector(start - center) + buff / radius,
            )
            if neg:
                raw_arc_points = raw_arc_points[::-1]
            self.set_points(center + radius * raw_arc_points)
        else:
            if buff > 0 and dist > 0:
                start = start + vect * (buff / dist)
                end = end - vect * (buff / dist)
            self.set_points_as_corners([start, end])
        return self

    def set_path_arc(self, new_value: float) -> Self:
        self.path_arc = new_value
        self.set_points_by_ends(self.start, self.end, self.buff, self.path_arc)
        return self

    def set_start_and_end_attrs(self, start: np.ndarray, end: np.ndarray) -> None:
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

    def pointify(
        self,
        item_or_point: Item | np.ndarray,
        direction: np.ndarray | None = None
    ) -> np.ndarray:
        """
        Take an argument passed into Line (or subclass) and turn
        it into a 3d point.
        """
        if isinstance(item_or_point, Item):
            item = item_or_point
            if direction is None:
                return item.get_center()
            else:
                return item.get_continuous_bbox_point(direction)
        else:
            point = item_or_point
            result = np.zeros(3)
            result[:len(point)] = point
            return result

    def put_start_and_end_on(self, start: np.ndarray, end: np.ndarray) -> Self:
        curr_start, curr_end = self.get_start_and_end()
        if np.isclose(curr_start, curr_end).all():
            # Handle null lines more gracefully
            self.set_points_by_ends(start, end, buff=0, path_arc=self.path_arc)
            return self
        return super().put_start_and_end_on(start, end)

    def get_vector(self) -> np.ndarray:
        return self.get_end() - self.get_start()

    def get_unit_vector(self) -> np.ndarray:
        return normalize(self.get_vector())

    def get_angle(self) -> float:
        return angle_of_vector(self.get_vector())

    def get_projection(self, point: np.ndarray) -> np.ndarray:
        """
        Return projection of a point onto the line
        """
        unit_vect = self.get_unit_vector()
        start = self.get_start()
        return start + np.dot(point - start, unit_vect) * unit_vect

    def get_slope(self) -> float:
        return np.tan(self.get_angle())

    def set_angle(self, angle: float, about_point: np.ndarray | None = None) -> Self:
        if about_point is None:
            about_point = self.get_start()
        self.rotate(
            angle - self.get_angle(),
            about_point=about_point,
        )
        return self
    
    def get_length(self) -> float:
        return get_norm(self.get_vector())

    def set_length(self, length: float, **kwargs) -> Self:
        self.scale(length / self.get_length(), False, **kwargs)
        return self

# TODO: DashedLine
# TODO: TangentLine
# TODO: Elbow

# TODO: [L] CubicBezier

