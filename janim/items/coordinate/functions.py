
from typing import Callable, Iterable

import numpy as np

from janim.constants import YELLOW
from janim.items.vitem import VItem
from janim.typing import JAnimColor, Vect
from janim.utils.bezier import PathBuilder


class ParametricCurve(VItem):
    def __init__(
        self,
        t_func: Callable[[float], Vect],
        t_range: tuple[float, float, float] = (0, 1, 0.1),
        epsilon: float = 1e-8,
        # TODO: automatically figure out discontinuities
        discontinuities: Iterable[float] = [],
        use_smoothing: bool = True,
        **kwargs
    ):
        self.t_func = t_func
        self.t_range = t_range
        self.epsilon = epsilon
        self.discontinuities = discontinuities
        self.use_smoothing = use_smoothing

        super().__init__(**kwargs)

        t_min, t_max, step = t_range
        builder = PathBuilder()

        jumps = np.array(discontinuities)
        jumps = jumps[(jumps > t_min) & (jumps < t_max)]
        boundary_times = [t_min, t_max, *(jumps - epsilon), *(jumps + epsilon)]
        boundary_times.sort()
        for t1, t2 in zip(boundary_times[0::2], boundary_times[1::2]):
            t_range = [*np.arange(t1, t2, step), t2]
            points = np.array([t_func(t) for t in t_range])

            builder.move_to(points[0])
            for point in points[1:]:
                builder.line_to(point)

        self.points.set(builder.get())
        if use_smoothing:
            self.points.make_approximately_smooth()
        if not self.points.has():
            self.points.set(np.array([t_func(t_min)]))

    def get_point_from_function(self, t: float) -> np.ndarray:
        return np.array(self.t_func(t))


class FunctionGraph(ParametricCurve):
    def __init__(
        self,
        function: Callable[[float], float],
        x_range: tuple[float, float, float] = (-8, 8, 0.25),
        color: JAnimColor = YELLOW,
        **kwargs
    ):
        super().__init__(
            lambda t: [t, function(t), 0],
            x_range,
            color=color,
            **kwargs
        )


# TODO: ImplicitFunction
