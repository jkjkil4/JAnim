
from janim.constants import *
from janim.items.item import Item, Point
from janim.items.vitem import VItem
from janim.utils.space_ops import (
    rotate_vector, angle_of_vector,
    find_intersection, get_norm
)

DEFAULT_DOT_RADIUS = 0.08
DEFAULT_SMALL_DOT_RADIUS = 0.04

class Arc(VItem):
    def __init__(
        self,
        start_angle: float = 0,
        angle: float = TAU / 4,
        radius: float = 1.0,
        n_components: int = 8,
        arc_center: np.ndarray = ORIGIN,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.set_points(
            Arc.create_quadratic_bezier_points(
                angle=angle,
                start_angle=start_angle,
                n_components=n_components
            ) * radius
        )
        self.shift(arc_center)

        self.center_point = Point(arc_center)
        self.add(self.center_point, is_helper=True)

    @staticmethod
    def create_quadratic_bezier_points(
        angle: float,
        start_angle: float = 0,
        n_components: int = 8
    ) -> np.ndarray:
        samples = np.array([
            [np.cos(a), np.sin(a), 0]
            for a in np.linspace(
                start_angle,
                start_angle + angle,
                2 * n_components + 1,
            )
        ])
        theta = angle / n_components
        samples[1::2] /= np.cos(theta / 2)

        points = np.zeros((3 * n_components, 3))
        points[0::3] = samples[0:-1:2]
        points[1::3] = samples[1::2]
        points[2::3] = samples[2::2]
        return points

    def get_arc_center(self) -> np.ndarray:
        return self.center_point.get_pos()

    def get_start_angle(self) -> float:
        angle = angle_of_vector(self.get_start() - self.get_arc_center())
        return angle % TAU

    def get_stop_angle(self) -> float:
        angle = angle_of_vector(self.get_end() - self.get_arc_center())
        return angle % TAU

    def move_arc_center_to(self, point: np.ndarray):
        self.shift(point - self.get_arc_center())
        return self

class ArcBetweenPoints(Arc):
    def __init__(
        self,
        start: np.ndarray,
        end: np.ndarray,
        angle: float = TAU / 4,
        **kwargs
    ):
        super().__init__(angle=angle, **kwargs)
        if angle == 0:
            self.set_points_as_corners([LEFT, RIGHT])
        self.put_start_and_end_on(start, end)

# TODO: CurvedArrow
# TODO: CurvedDoubleArrow

class Circle(Arc):
    def __init__(self, **kwargs):
        super().__init__(0, TAU, **kwargs)

    def surround(
        self,
        item: Item,
        dim_to_match: int = 0,
        stretch: bool = False,
        buff: float = MED_SMALL_BUFF
    ):
        # Ignores dim_to_match and stretch; result will always be a circle
        # TODO: [L] Perhaps create an ellipse class to handle singele-dimension stretching

        self.replace(item, dim_to_match, stretch)
        self.stretch((self.get_width() + 2 * buff) / self.get_width(), 0)
        self.stretch((self.get_height() + 2 * buff) / self.get_height(), 1)

    def point_at_angle(self, angle: float) -> np.ndarray:
        start_angle = self.get_start_angle()
        return self.point_from_proportion(
            (angle - start_angle) / TAU
        )

    def get_radius(self) -> float:
        return get_norm(self.get_start() - self.get_center())
    

class Dot(Circle):
    def __init__(
        self,
        point: np.ndarray = ORIGIN,
        radius: float = DEFAULT_DOT_RADIUS,
        stroke_width: float = 0,
        fill_opacity: float = 1.0,
        **kwargs
    ):
        super().__init__(
            arc_center=point,
            radius=radius,
            stroke_width=stroke_width,
            fill_opacity=fill_opacity,
            **kwargs
        )

class SmallDot(Dot):
    def __init__(self, radius: float = DEFAULT_SMALL_DOT_RADIUS, **kwargs):
        super().__init__(radius=radius, **kwargs)


class Ellipse(Circle):
    def __init__(
        self,
        width: float = 2,
        height: float = 1,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.set_size(width, height)

class AnnularSector(VItem):
    def __init__(
        self,
        inner_radius: float = 0.5,
        outer_radius: float = 1,
        start_angle: float = 0,
        angle: float = TAU / 4,
        arc_center: np.ndarray = ORIGIN,
        n_components: int = 8,
        **kwargs
    ):
        super().__init__(**kwargs)

        unit = Arc.create_quadratic_bezier_points(
            angle=angle,
            start_angle=start_angle,
            n_components=n_components
        )

        inner_arc, outer_arc = (
            unit * radius + arc_center
            for radius in (inner_radius, outer_radius)
        )
        inner_arc = inner_arc[::-1]
        self.append_points(outer_arc)
        self.add_line_to(inner_arc[0])
        self.append_points(inner_arc)
        self.add_line_to(outer_arc[0])

        self.center_point = Point(arc_center)
        self.add(self.center_point, is_helper=True)

    def get_arc_center(self) -> np.ndarray:
        return self.center_point.get_pos()

    def move_arc_center_to(self, point: np.ndarray):
        self.shift(point - self.get_arc_center())
        return self

class Sector(Arc):
    def __init__(self, arc_center: np.ndarray = ORIGIN, **kwargs):
        super().__init__(arc_center=arc_center, **kwargs)

        self.add_points_as_corners([arc_center, self.get_points()[0]])

class Annulus(VItem):
    def __init__(
        self,
        outer_radius: float = 1,
        inner_radius: float = 0.5,
        arc_center: np.ndarray = ORIGIN,
        n_components: int = 8,
        fill_opacity: float = 0.5,
        **kwargs
    ):
        super().__init__(fill_opacity=fill_opacity, **kwargs)

        unit = Arc.create_quadratic_bezier_points(
            TAU, 0,
            n_components
        )
        
        inner, outer = (
            unit * radius + arc_center
            for radius in (inner_radius, outer_radius)
        )
        outer = outer[::-1]
        self.append_points(outer)
        self.append_points(inner)

