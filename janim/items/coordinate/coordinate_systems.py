
from abc import ABCMeta, abstractmethod
from typing import Callable, Iterable, Self, Sequence

import numpy as np

from janim.components.component import CmptInfo
from janim.components.points import Cmpt_Points
from janim.components.vpoints import Cmpt_VPoints
from janim.constants import BLUE_D, DEGREES, DL, ORIGIN, SMALL_BUFF, UP, WHITE
from janim.items.coordinate.functions import ParametricCurve
from janim.items.coordinate.number_line import NumberLine
from janim.items.geometry.line import Line
from janim.items.item import _ItemMeta
from janim.items.points import Group
from janim.items.vitem import DEFAULT_STROKE_RADIUS
from janim.typing import RangeSpecifier, Vect, VectArray
from janim.utils.dict_ops import merge_dicts_recursively
from janim.utils.space_ops import cross

DEFAULT_X_RANGE = (-8.0, 8.0, 1.0)
DEFAULT_Y_RANGE = (-4.0, 4.0, 1.0)


class _ItemMeta_ABCMeta(_ItemMeta, ABCMeta):
    pass


class CoordinateSystem(metaclass=ABCMeta):
    def __init__(
        self,
        *args,
        num_sampled_graph_points_per_tick,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.num_sampled_graph_points_per_tick = num_sampled_graph_points_per_tick

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

    def get_origin(self) -> np.ndarray:
        axes = self.get_axes()
        return axes[0].number_to_point(0)

    def coords_to_point(self, *coords: float) -> np.ndarray:
        '''
        传入坐标得到对应的位置

        例如 ``c2p(1, 3)`` 得到 (1,3) 的位置
        '''
        axes = self.get_axes()
        origin = self.get_origin()
        return origin + sum(
            axis.number_to_point(coord) - origin
            for axis, coord in zip(axes, coords)
        )

    def coords_array_to_points(self, coords_array: VectArray) -> np.ndarray:
        '''
        传入一组坐标得到对应的一组位置

        例如 ``c2p([[1, 3], [2, 1], [-1, -1]])`` 得到对应的三个位置
        '''
        axes = self.get_axes()
        origin = self.get_origin()
        coords_array = np.asarray(coords_array)
        return origin + sum(
            axis.number_to_point(coord) - origin
            for axis, coord in zip(axes, coords_array.T)
        )

    def c2p(self, *coords: float) -> np.ndarray:
        ''':meth:`coords_to_point` 的缩写'''
        return self.coords_to_point(*coords)

    def point_to_coords3d(self, point: Vect | Iterable[Vect]) -> np.ndarray:
        '''
        传入位置得到对应的坐标（但是会扩张为三维坐标；对于二维坐标系来说，第三个分量则表示距离二维平面的距离）

        也可以传入一组位置得到一组对应的坐标
        '''
        axes = self.get_axes()
        origin = self.get_origin()
        vectors = [axe.number_to_point(1) - origin for axe in axes]
        if len(vectors) == 2:
            vectors.append(cross(vectors[0], vectors[1]))
        else:
            assert len(vectors) == 3
        mat = np.linalg.inv(np.column_stack(vectors))
        return (point - origin) @ mat.T

    def p2c3d(self, point: Vect | Iterable[Vect]) -> np.ndarray:
        ''':meth:`point_to_coords3d` 的简写'''
        return self.point_to_coords3d(point)

    def point_to_coords(self, point: Vect | Iterable[Vect]) -> np.ndarray:
        '''
        传入位置得到对应坐标

        也可以传入一组位置得到一组对应的坐标
        '''
        axes = self.get_axes()
        return self.point_to_coords3d(point)[:len(axes)]

    def p2c(self, point: Vect | Iterable[Vect]) -> np.ndarray:
        ''':meth:`point_to_coords` 的缩写'''
        return self.point_to_coords(point)

    def number_to_point(self, number: complex | float) -> np.ndarray:
        '''传入复数得到对应位置'''
        number = complex(number)
        return self.coords_to_point(number.real, number.imag)

    def n2p(self, number: complex | float) -> np.ndarray:
        ''':meth:`number_to_point` 的缩写'''
        return self.number_to_point(number)

    def point_to_number(self, point: Vect) -> complex:
        '''传入位置得到对应复数'''
        x, y = self.point_to_coords3d(point)[:2]
        return complex(x, y)

    def p2n(self, point: Vect) -> complex:
        ''':meth:`point_to_number` 的缩写'''
        return self.point_to_number(point)


class Axes(CoordinateSystem, Group, metaclass=_ItemMeta_ABCMeta):
    axis_config_d: dict = dict(
        numbers_to_exclude=[0]
    )
    x_axis_config_d: dict = {}
    y_axis_config_d: dict = dict(
        line_to_number_direction=UP
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
        self.x_range = x_range
        self.y_range = y_range

        axis_config = dict(**axis_config, unit_size=unit_size)
        self.x_axis = CoordinateSystem.create_axis(
            x_range,
            axis_config=merge_dicts_recursively(
                self.axis_config_d,
                self.x_axis_config_d,
                axis_config,
                x_axis_config
            ),
            length=width
        )
        self.y_axis = CoordinateSystem.create_axis(
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

        super().__init__(
            self.x_axis,
            self.y_axis,
            num_sampled_graph_points_per_tick=num_sampled_graph_points_per_tick,
            **kwargs
        )

    def get_axes(self) -> list[NumberLine]:
        return [self.x_axis, self.y_axis]

    def get_graph(
        self,
        function: Callable[[float], float],
        x_range: Sequence[float] | None = None,
        bind: bool = True,
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

        if bind:
            Cmpt_Points.apply_points_fn.connect(
                self.points,
                lambda func, about_point: graph.points.apply_points_fn(func,
                                                                       about_point=about_point,
                                                                       about_edge=None)
            )

        return graph

    def get_parametric_curve(
        self,
        function: Callable[[float], Vect],
        bind: bool = True,
        **kwargs
    ):
        graph = ParametricCurve(
            lambda t: self.coords_to_point(*function(t)),
            **kwargs
        )

        if bind:
            Cmpt_Points.apply_points_fn.connect(
                self.points,
                lambda func, about_point: graph.points.apply_points_fn(func,
                                                                       about_point=about_point,
                                                                       about_edge=None)
            )

        return graph


# TODO: ThreeDAxes


class CmptVPoints_NumberPlaneImpl(Cmpt_VPoints, impl=True):
    def prepare_for_nonlinear_transform(self, num_inserted_curves: int = 50, *, root_only=False) -> Self:
        for cmpt in self.walk_same_cmpt_of_self_and_descendants_without_mock(root_only):
            if not isinstance(cmpt, Cmpt_VPoints) or not cmpt.has():
                continue

            curves_count = cmpt.curves_count()
            if num_inserted_curves > curves_count:
                cmpt.insert_n_curves(num_inserted_curves - curves_count)
            cmpt.make_smooth_after_applying_functions = True

        return self


class NumberPlane(Axes):
    points = CmptInfo(CmptVPoints_NumberPlaneImpl)

    background_line_style_d: dict = dict(
        stroke_color=BLUE_D,
        stroke_radius=0.01,
    )
    axis_config_d: dict = dict(
        stroke_color=WHITE,
        stroke_radius=0.01,
        include_ticks=False,
        include_tip=False,
        line_to_number_buff=SMALL_BUFF,
        line_to_number_direction=DL
    )
    y_axis_config_d: dict = dict(
        line_to_number_direction=DL
    )

    def __init__(
        self,
        x_range: RangeSpecifier = DEFAULT_X_RANGE,
        y_range: RangeSpecifier = DEFAULT_Y_RANGE,
        background_line_style: dict = dict(),
        # Defaults to a faded version of line_config
        faded_line_style: dict = dict(),
        faded_line_ratio: int = 4,
        **kwargs
    ):
        super().__init__(
            x_range,
            y_range,
            **kwargs
        )
        self.background_line_style = merge_dicts_recursively(self.background_line_style_d, background_line_style)
        self.faded_line_style = dict(faded_line_style)
        self.faded_line_ratio = faded_line_ratio
        self._init_background_lines()

    def _init_background_lines(self) -> None:
        if not self.faded_line_style:
            style = dict(self.background_line_style)

            for key in ('fill_alpha', 'stroke_alpha', 'alpha'):
                style[key] = 0.5 * style.get(key, 1)

            style['stroke_radius'] = 0.5 * style.get('stroke_radius', DEFAULT_STROKE_RADIUS)

            self.faded_line_style = style

        x_lines1, x_lines2 = self.get_lines_parallel_to_axis(self.x_axis, self.y_axis)
        y_lines1, y_lines2 = self.get_lines_parallel_to_axis(self.y_axis, self.x_axis)
        self.background_lines = Group(*x_lines1, *y_lines1)
        self.faded_lines = Group(*x_lines2, *y_lines2)

        self.background_lines.set(**self.background_line_style)
        self.faded_lines.set(**self.faded_line_style)

        self.add(
            self.faded_lines,
            self.background_lines,
            insert=True
        )
        self.depth.arrange()

    def get_lines_parallel_to_axis(
        self,
        axis1: NumberLine,
        axis2: NumberLine
    ) -> tuple[Group, Group]:
        freq = axis2.x_step
        ratio = self.faded_line_ratio
        line = Line(axis1.points.get_start(), axis1.points.get_end())
        dense_freq = (1 + ratio)
        step = (1 / dense_freq) * freq

        lines1 = Group()
        lines2 = Group()
        inputs = np.arange(axis2.x_min, axis2.x_max + step, step)
        for i, x in enumerate(inputs):
            if abs(x) < 1e-8:
                continue
            new_line = line.copy()
            new_line.points.shift(axis2.n2p(x) - axis2.n2p(0))
            if i % (1 + ratio) == 0:
                lines1.add(new_line)
            else:
                lines2.add(new_line)
        return lines1, lines2
