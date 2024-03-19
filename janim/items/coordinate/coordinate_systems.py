
from abc import ABCMeta, abstractmethod
from typing import Callable, Iterable, Sequence

import numpy as np

from janim.constants import DEGREES, LEFT, ORIGIN
from janim.items.coordinate.functions import ParametricCurve
from janim.items.coordinate.number_line import NumberLine
from janim.items.item import _ItemMeta
from janim.items.points import Group
from janim.typing import RangeSpecifier, Vect
from janim.utils.dict_ops import merge_dicts_recursively

DEFAULT_X_RANGE = (-8.0, 8.0, 1.0)
DEFAULT_Y_RANGE = (-4.0, 4.0, 1.0)


class _ItemMeta_ABCMeta(_ItemMeta, ABCMeta):
    pass


class CoordinateSystem(metaclass=ABCMeta):
    @staticmethod
    def create_axis(
        range: RangeSpecifier,
        axis_config: dict,
        length: float | None
    ) -> NumberLine:
        axis = NumberLine(range, width=length, **axis_config)
        axis.points.shift(-axis.n2p(0))
        return axis

    @abstractmethod
    def get_axes(self) -> list[NumberLine]:
        pass

    def coords_to_point(self, *coords: float | Iterable[float]) -> np.ndarray:
        axes = self.get_axes()
        origin = axes[0].number_to_point(0)
        return origin + sum(
            axis.number_to_point(coord) - origin
            for axis, coord in zip(axes, coords)
        )

    def point_to_coords(self, point: Vect | Iterable[Vect]) -> np.ndarray:
        raise NotImplementedError()     # TODO: point_to_coords

    def c2p(self, *coords: float | np.ndarray) -> np.ndarray:
        ''':meth:`coords_to_point` 的缩写'''
        return self.coords_to_point(*coords)

    def p2c(self, point: Vect | Iterable[Vect]) -> np.ndarray:
        ''':meth:`point_to_coords` 的缩写'''
        return self.point_to_coords(self, point)

    def get_origin(self) -> np.ndarray:
        return self.c2p(*[0] * len(self.get_axes()))


class Axes(Group, CoordinateSystem, metaclass=_ItemMeta_ABCMeta):
    axis_config_d: dict = dict(
        numbers_to_exclude=[0]
    )
    x_axis_config_d: dict = {}
    y_axis_config_d: dict = dict(
        line_to_number_direction=LEFT
    )

    def __init__(
        self,
        x_range: RangeSpecifier = DEFAULT_X_RANGE,
        y_range: RangeSpecifier = DEFAULT_Y_RANGE,
        *,
        num_sampled_graph_points_per_tick: int = 5,
        axis_config: dict = {},
        x_axis_config: dict = {},
        y_axis_config: dict = {},
        height: float | None = None,
        width: float | None = None,
        unit_size: float = 1.0,
        **kwargs
    ):
        # REFACTOR: 将 num_sampled_graph_points_per_tick 提取到 CoordinateSystem 中？
        CoordinateSystem.__init__(self)
        self.x_range = x_range
        self.y_range = y_range
        self.num_sampled_graph_points_per_tick = num_sampled_graph_points_per_tick

        axis_config = dict(**axis_config, unit_size=unit_size)
        self.x_axis = self.create_axis(
            x_range,
            axis_config=merge_dicts_recursively(
                self.axis_config_d,
                self.x_axis_config_d,
                axis_config,
                x_axis_config
            ),
            length=width
        )
        self.y_axis = self.create_axis(
            y_range,
            axis_config=merge_dicts_recursively(
                self.axis_config_d,
                self.y_axis_config_d,
                axis_config,
                y_axis_config
            ),
            length=height
        )
        self.y_axis.points.rotate(90 * DEGREES, about_point=ORIGIN)

        Group.__init__(self, self.x_axis, self.y_axis, **kwargs)

    def get_axes(self) -> list[NumberLine]:
        return [self.x_axis, self.y_axis]

    def get_graph(
        self,
        function: Callable[[float], float],
        x_range: Sequence[float] | None = None,
        # TODO: bind
        **kwargs
    ) -> ParametricCurve:
        x_range = x_range or self.x_range
        t_range = np.ones(3)
        t_range[:len(x_range)] = x_range
        # 对于坐标轴，x_range 的第三个元素是刻度步长
        # 所以对于函数，需要除以 num_sampled_graph_points_per_tick
        t_range[2] /= self.num_sampled_graph_points_per_tick

        graph = ParametricCurve(
            lambda t: self.c2p(t, function(t)),
            t_range=tuple(t_range),
            **kwargs
        )
        return graph
