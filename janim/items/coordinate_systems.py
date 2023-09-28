from __future__ import annotations
from abc import ABCMeta, abstractmethod

from janim.typing import RangeSpecifier
from typing import TypeVar, Type, Sequence
T = TypeVar('T', bound='Item')

from janim.items.item import Item
from janim.items.vitem import VGroup
from janim.items.text.tex import Tex
from janim.items.geometry.line import DashedLine
from janim.items.number_line import NumberLine
from janim.utils.dict_ops import merge_dicts_recursively
from janim.constants import *

DEFAULT_X_RANGE = (-8.0, 8.0, 1.0)
DEFAULT_Y_RANGE = (-4.0, 4.0, 1.0)

class CoordinateSystem(metaclass=ABCMeta):
    def __init__(
        self,
        x_range: RangeSpecifier = DEFAULT_X_RANGE,
        y_range: RangeSpecifier = DEFAULT_Y_RANGE,
        *,
        dimension: int = 2,
        width: float = FRAME_WIDTH,
        height: float = FRAME_HEIGHT,
        num_sampled_graph_points_per_tick: int = 20
    ) -> None:
        self.dimension = dimension
        self.x_range = np.array(x_range)
        self.y_range = np.array(y_range)
        self.width = width
        self.height = height
        self.num_sampled_graph_points_per_tick = num_sampled_graph_points_per_tick

    @abstractmethod
    def coords_to_point(self, *coords: float) -> np.ndarray: ...

    @abstractmethod
    def point_to_coords(self, point: np.ndarray) -> tuple[float, ...]: ...

    def c2p(self, *coords: float) -> np.ndarray:
        '''coords_to_point 的简写'''
        return self.coords_to_point(*coords)
    
    def p2c(self, point: np.ndarray) -> tuple[float, ...]:
        '''point_to_coords 的简写'''
        return self.point_to_coords(point)
    
    def get_origin(self) -> np.ndarray:
        return self.c2p(*[0] * self.dimension)
    
    @abstractmethod
    def get_axes(self) -> VGroup: ...

    @abstractmethod
    def get_all_ranges(self) -> list[np.ndarray]: ...

    def get_axis(self, index: int) -> NumberLine:
        return self.get_axes()[index]
    
    def get_x_axis(self) -> NumberLine:
        return self.get_axis(0)
    
    def get_y_axis(self) -> NumberLine:
        return self.get_axis(1)
    
    def get_z_axis(self) -> NumberLine:
        return self.get_axis(2)
    
    def get_x_axis_label(
        self,
        label_tex: str,
        edge: np.ndarray = RIGHT,
        direction: np.ndarray = DL,
        **kwargs
    ) -> Tex:
        return self.get_axis_label(
            label_tex, self.get_x_axis(),
            edge, direction, **kwargs
        )

    def get_y_axis_label(
        self,
        label_tex: str,
        edge: np.ndarray = UP,
        direction: np.ndarray = DR,
        **kwargs
    ) -> Tex:
        return self.get_axis_label(
            label_tex, self.get_y_axis(),
            edge, direction, **kwargs
        )

    def get_axis_label(
        self,
        label_tex: str,
        axis: np.ndarray,
        edge: np.ndarray,
        direction: np.ndarray,
        buff: float = MED_SMALL_BUFF
    ) -> Tex:
        label = Tex(label_tex)
        label.next_to(
            axis.get_edge_center(edge), direction,
            buff=buff
        )
        label.shift_onto_screen(buff=MED_SMALL_BUFF)
        return label

    def get_axis_labels(
        self,
        x_label_tex: str = "x",
        y_label_tex: str = "y"
    ) -> VGroup:
        self.axis_labels = VGroup(
            self.get_x_axis_label(x_label_tex),
            self.get_y_axis_label(y_label_tex),
        )
        return self.axis_labels

    def get_line_from_axis_to_point(
        self, 
        index: int,
        point: np.ndarray,
        line_func: Type[T] = DashedLine,
        color: JAnimColor = GREY_A,
        stroke_width: float = 2
    ) -> T:
        axis = self.get_axis(index)
        line = line_func(axis.get_projection(point), point)
        line.set_stroke(color, stroke_width)
        return line

    def get_v_line(self, point: np.ndarray, **kwargs):
        return self.get_line_from_axis_to_point(0, point, **kwargs)

    def get_h_line(self, point: np.ndarray, **kwargs):
        return self.get_line_from_axis_to_point(1, point, **kwargs)
    
    # TODO: get_graph 以及相关的方法

    # Useful for graphing
    # def get_graph(
    #     self,
    #     function: Callable[[float], float],
    #     x_range: Sequence[float] | None = None,
    #     **kwargs
    # ) -> ParametricCurve:
    #     t_range = np.array(self.x_range, dtype=float)
    #     if x_range is not None:
    #         t_range[:len(x_range)] = x_range
    #     # For axes, the third coordinate of x_range indicates
    #     # tick frequency.  But for functions, it indicates a
    #     # sample frequency
    #     if x_range is None or len(x_range) < 3:
    #         t_range[2] /= self.num_sampled_graph_points_per_tick

    #     graph = ParametricCurve(
    #         lambda t: self.c2p(t, function(t)),
    #         t_range=t_range,
    #         **kwargs
    #     )
    #     graph.underlying_function = function
    #     graph.x_range = x_range
    #     return graph

    # def get_parametric_curve(
    #     self,
    #     function: Callable[[float], np.ndarray],
    #     **kwargs
    # ) -> ParametricCurve:
    #     dim = self.dimension
    #     graph = ParametricCurve(
    #         lambda t: self.coords_to_point(*function(t)[:dim]),
    #         **kwargs
    #     )
    #     graph.underlying_function = function
    #     return graph

    # def input_to_graph_point(
    #     self,
    #     x: float,
    #     graph: ParametricCurve
    # ) -> np.ndarray | None:
    #     if hasattr(graph, "underlying_function"):
    #         return self.coords_to_point(x, graph.underlying_function(x))
    #     else:
    #         alpha = binary_search(
    #             function=lambda a: self.point_to_coords(
    #                 graph.quick_point_from_proportion(a)
    #             )[0],
    #             target=x,
    #             lower_bound=self.x_range[0],
    #             upper_bound=self.x_range[1],
    #         )
    #         if alpha is not None:
    #             return graph.quick_point_from_proportion(alpha)
    #         else:
    #             return None

    # def i2gp(self, x: float, graph: ParametricCurve) -> np.ndarray | None:
    #     """
    #     Alias for input_to_graph_point
    #     """
    #     return self.input_to_graph_point(x, graph)

    # def get_graph_label(
    #     self,
    #     graph: ParametricCurve,
    #     label: str | Mobject = "f(x)",
    #     x: float | None = None,
    #     direction: np.ndarray = RIGHT,
    #     buff: float = MED_SMALL_BUFF,
    #     color: ManimColor | None = None
    # ) -> Tex | Mobject:
    #     if isinstance(label, str):
    #         label = Tex(label)
    #     if color is None:
    #         label.match_color(graph)
    #     if x is None:
    #         # Searching from the right, find a point
    #         # whose y value is in bounds
    #         max_y = FRAME_Y_RADIUS - label.get_height()
    #         max_x = FRAME_X_RADIUS - label.get_width()
    #         for x0 in np.arange(*self.x_range)[::-1]:
    #             pt = self.i2gp(x0, graph)
    #             if abs(pt[0]) < max_x and abs(pt[1]) < max_y:
    #                 x = x0
    #                 break
    #         if x is None:
    #             x = self.x_range[1]

    #     point = self.input_to_graph_point(x, graph)
    #     angle = self.angle_of_tangent(x, graph)
    #     normal = rotate_vector(RIGHT, angle + 90 * DEGREES)
    #     if normal[1] < 0:
    #         normal *= -1
    #     label.next_to(point, normal, buff=buff)
    #     label.shift_onto_screen()
    #     return label

    # def get_v_line_to_graph(self, x: float, graph: ParametricCurve, **kwargs):
    #     return self.get_v_line(self.i2gp(x, graph), **kwargs)

    # def get_h_line_to_graph(self, x: float, graph: ParametricCurve, **kwargs):
    #     return self.get_h_line(self.i2gp(x, graph), **kwargs)

    # # For calculus
    # def angle_of_tangent(
    #     self,
    #     x: float,
    #     graph: ParametricCurve,
    #     dx: float = EPSILON
    # ) -> float:
    #     p0 = self.input_to_graph_point(x, graph)
    #     p1 = self.input_to_graph_point(x + dx, graph)
    #     return angle_of_vector(p1 - p0)

    # def slope_of_tangent(
    #     self,
    #     x: float,
    #     graph: ParametricCurve,
    #     **kwargs
    # ) -> float:
    #     return np.tan(self.angle_of_tangent(x, graph, **kwargs))

    # def get_tangent_line(
    #     self,
    #     x: float,
    #     graph: ParametricCurve,
    #     length: float = 5,
    #     line_func: Type[T] = Line
    # ) -> T:
    #     line = line_func(LEFT, RIGHT)
    #     line.set_width(length)
    #     line.rotate(self.angle_of_tangent(x, graph))
    #     line.move_to(self.input_to_graph_point(x, graph))
    #     return line

    # def get_riemann_rectangles(
    #     self,
    #     graph: ParametricCurve,
    #     x_range: Sequence[float] = None,
    #     dx: float | None = None,
    #     input_sample_type: str = "left",
    #     stroke_width: float = 1,
    #     stroke_color: ManimColor = BLACK,
    #     fill_opacity: float = 1,
    #     colors: Iterable[ManimColor] = (BLUE, GREEN),
    #     stroke_background: bool = True,
    #     show_signed_area: bool = True
    # ) -> VGroup:
    #     if x_range is None:
    #         x_range = self.x_range[:2]
    #     if dx is None:
    #         dx = self.x_range[2]
    #     if len(x_range) < 3:
    #         x_range = [*x_range, dx]

    #     rects = []
    #     xs = np.arange(*x_range)
    #     for x0, x1 in zip(xs, xs[1:]):
    #         if input_sample_type == "left":
    #             sample = x0
    #         elif input_sample_type == "right":
    #             sample = x1
    #         elif input_sample_type == "center":
    #             sample = 0.5 * x0 + 0.5 * x1
    #         else:
    #             raise Exception("Invalid input sample type")
    #         height = get_norm(
    #             self.i2gp(sample, graph) - self.c2p(sample, 0)
    #         )
    #         rect = Rectangle(width=self.x_axis.n2p(x1)[0] - self.x_axis.n2p(x0)[0], 
    #                          height=height)
    #         rect.move_to(self.c2p(x0, 0), DL)
    #         rects.append(rect)
    #     result = VGroup(*rects)
    #     result.set_submobject_colors_by_gradient(*colors)
    #     result.set_style(
    #         stroke_width=stroke_width,
    #         stroke_color=stroke_color,
    #         fill_opacity=fill_opacity,
    #         stroke_background=stroke_background
    #     )
    #     return result

    def get_area_under_graph(self, graph, x_range, fill_color=BLUE, fill_opacity=1):
        # TODO: get_area_under_graph
        pass

class Axes(VGroup, CoordinateSystem):
    default_axis_config: dict = dict(
        numbers_to_exclude=[0]
    )
    default_x_axis_config: dict = {}
    default_y_axis_config: dict = dict(
        line_to_number_direction=LEFT
    )

    def __init__(
        self,
        x_range: RangeSpecifier = DEFAULT_X_RANGE,
        y_range: RangeSpecifier = DEFAULT_Y_RANGE,
        *,
        axis_config: dict = {},
        x_axis_config: dict = {},
        y_axis_config: dict = {},
        height: float | None = None,
        width: float | None = None,
        unit_size: float = 1.0,
        **kwargs
    ):
        CoordinateSystem.__init__(self, x_range, y_range, **kwargs)
        VGroup.__init__(self, **kwargs)

        axis_config = dict(**axis_config, unit_size=unit_size)
        self.x_axis = self.create_axis(
            self.x_range,
            axis_config=merge_dicts_recursively(
                self.default_axis_config,
                self.default_x_axis_config,
                axis_config,
                x_axis_config
            ),
            length=width,
        )
        self.y_axis = self.create_axis(
            self.y_range,
            axis_config=merge_dicts_recursively(
                self.default_axis_config,
                self.default_y_axis_config,
                axis_config,
                y_axis_config
            ),
            length=height,
        )
        self.y_axis.rotate(90 * DEGREES, about_point=ORIGIN)
        # Add as a separate group in case various other
        # mobjects are added to self, as for example in
        # NumberPlane below
        self.axes = VGroup(self.x_axis, self.y_axis)
        self.add(*self.axes)
        self.to_center()

    @staticmethod
    def create_axis(
        range_terms: RangeSpecifier,
        axis_config: dict,
        length: float | None
    ) -> NumberLine:
        axis = NumberLine(range_terms, width=length, **axis_config)
        axis.shift(-axis.n2p(0))
        return axis
    
    def coords_to_point(self, *coords: float | np.ndarray) -> np.ndarray:
        origin = self.x_axis.number_to_point(0)
        return origin + sum(
            axis.number_to_point(coord) - origin
            for axis, coord in zip(self.get_axes(), coords)
        )

    def point_to_coords(self, point: np.ndarray | Iterable[np.ndarray]) -> np.ndarray:
        return tuple([
            axis.point_to_number(point)
            for axis in self.get_axes()
        ])
    
    def get_axes(self) -> VGroup:
        return self.axes
    
    def get_all_ranges(self) -> list[Sequence[float]]:
        return [self.x_range, self.y_range]
    
    def add_coordinate_labels(
        self,
        x_values: Iterable[float] | None = None,
        y_values: Iterable[float] | None = None,
        **kwargs
    ) -> VGroup:
        axes = self.get_axes()
        self.coordinate_labels = VGroup()
        for axis, values in zip(axes, [x_values, y_values]):
            labels = axis.add_numbers(values, **kwargs)
            self.coordinate_labels.add(labels)
        return self.coordinate_labels
    
# TODO: ThreeDAxes
# TODO: NumberPlane
# TODO: ComplexPlane
