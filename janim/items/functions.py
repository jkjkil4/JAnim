from __future__ import annotations
from typing import Callable, Sequence
from janim.typing import Self, RangeSpecifier

from janim.constants import *
from janim.items.vitem import VItem

DEFAULT_T_RANGE = [0, 1, 0.1]
DEFAULT_X_RANGE = [-8, 8, 0.25]

class ParametricCurve(VItem):
    def __init__(
        self,
        t_func: Callable[[float], np.ndarray],
        t_range: RangeSpecifier = DEFAULT_T_RANGE,
        *,
        epsilon: float = 1e-8,
        discontinuities: Iterable[float] = [],
        use_smoothing: bool = True,
        **kwargs
    ) -> None:
        self.t_range = DEFAULT_T_RANGE
        self.t_range[:len(t_range)] = t_range
        self.t_func = t_func
        self.epsilon = epsilon
        self.discontinuities = discontinuities
        self.use_smoothing = use_smoothing

        super().__init__(**kwargs)

        self.init_curve_points()

    def get_point_from_function(self, t: float) -> np.ndarray:
        return self.t_func(t)
    
    def init_curve_points(self) -> Self:
        t_min, t_max, step = self.t_range

        jumps = np.array(self.discontinuities)
        jumps = jumps[(jumps > t_min) & (jumps < t_max)]
        boundary_times = [t_min, t_max, *(jumps - self.epsilon), *(jumps + self.epsilon)]
        boundary_times.sort()
        for t1, t2 in zip(boundary_times[0::2], boundary_times[1::2]):
            t_range = [*np.arange(t1, t2, step), t2]
            points = np.array([self.t_func(t) for t in t_range])
            self.path_move_to(points[0])
            self.add_points_as_corners(points[1:])
        if self.use_smoothing:
            self.make_approximately_smooth()
        if not self.has_points():
            self.set_points([self.t_func(t_min)])
        return self

    def get_t_func(self):
        return self.t_func

    def get_function(self):
        if hasattr(self, "underlying_function"):
            return self.underlying_function
        if hasattr(self, "function"):
            return self.function

    def get_x_range(self):
        if hasattr(self, "x_range"):
            return self.x_range
        
class FunctionGraph(ParametricCurve):
    def __init__(
        self,
        function: Callable[[float], float],
        x_range: RangeSpecifier = DEFAULT_X_RANGE,
        *,
        color: JAnimColor = YELLOW,
        **kwargs
    ) -> None:
        self.function = function

        self.x_range = DEFAULT_X_RANGE
        self.x_range[:len(x_range)] = x_range

        super().__init__(
            lambda t: [t, function(t), 0], 
            self.x_range, 
            color=color, 
            **kwargs
        )

# TODO: ImplicitFunction

