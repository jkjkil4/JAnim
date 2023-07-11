
from janim.constants import *
from janim.items.vitem import VItem
from janim.utils.space_ops import rotate_vector, find_intersection, angle_of_vector

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

        self.set_points(Arc.create_quadratic_bezier_points(
            angle=angle,
            start_angle=start_angle,
            n_components=n_components
        ))
        self.scale(radius, about_point=ORIGIN)
        self.shift(arc_center)

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
        """
        Looks at the normals to the first two
        anchors, and finds their intersection points
        """
        # First two anchors and handles
        a1, h, a2 = self.get_points()[:3]
        # Tangent vectors
        t1 = h - a1
        t2 = h - a2
        # Normals
        n1 = rotate_vector(t1, TAU / 4)
        n2 = rotate_vector(t2, TAU / 4)
        return find_intersection(a1, n1, a2, n2)

    def get_start_angle(self) -> float:
        angle = angle_of_vector(self.get_start() - self.get_arc_center())
        return angle % TAU

    def get_stop_angle(self) -> float:
        angle = angle_of_vector(self.get_end() - self.get_arc_center())
        return angle % TAU

    def move_arc_center_to(self, point: np.ndarray):
        self.shift(point - self.get_arc_center())
        return self
