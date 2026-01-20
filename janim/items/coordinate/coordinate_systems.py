
from abc import ABCMeta, abstractmethod
from typing import Callable, Iterable, Self

import numpy as np

from janim.components.component import CmptInfo
from janim.components.points import Cmpt_Points
from janim.components.vpoints import Cmpt_VPoints
from janim.constants import (BLUE, BLUE_D, DEGREES, DL, ORIGIN, OUT, PI, RIGHT,
                             SMALL_BUFF, UP, WHITE)
from janim.items.coordinate.functions import ParametricCurve
from janim.items.coordinate.number_line import NumberLine
from janim.items.geometry.line import Line
from janim.items.geometry.polygon import Polygon
from janim.items.item import _ItemMeta
from janim.items.points import Group, MarkedItem, NamedGroupMixin, Points
from janim.items.svg.typst import TypstMath
from janim.items.vitem import DEFAULT_STROKE_RADIUS
from janim.typing import JAnimColor, RangeSpecifier, Vect, VectArray
from janim.utils.dict_ops import merge_dicts_recursively
from janim.utils.space_ops import angle_of_vector, cross

DEFAULT_X_RANGE = (-8.0, 8.0, 1)
DEFAULT_Y_RANGE = (-4.0, 4.0, 1)


class _ItemMeta_ABCMeta(_ItemMeta, ABCMeta):
    pass


class CoordinateSystem(metaclass=ABCMeta):
    """
    坐标系统抽象类

    具体实现请参考 :class:`Axes` :class:`ThreeDAxes` 以及 :class:`NumberPlane`
    """

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
        axis = NumberLine(range, length=length, center=False, **axis_config)
        return axis

    @abstractmethod
    def get_axes(self) -> list[NumberLine]:
        """
        得到由各方向 :class:`~.NumberLine` 所组成的列表
        """
        pass

    def get_origin(self) -> np.ndarray:
        axes = self.get_axes()
        return axes[0].mark.get()

    def coords_to_point(self, *coords: float) -> np.ndarray:
        """
        传入坐标得到对应的位置

        例如 ``c2p(1, 3)`` 得到 (1,3) 的位置
        """
        axes = self.get_axes()
        origin = self.get_origin()
        return origin + sum(
            axis.number_to_point(coord) - origin
            for axis, coord in zip(axes, coords)
        )

    def coords_array_to_points(self, coords_array: VectArray) -> np.ndarray:
        """
        传入一组坐标得到对应的一组位置

        例如 ``c2p([[1, 3], [2, 1], [-1, -1]])`` 得到对应的三个位置
        """
        axes = self.get_axes()
        origin = self.get_origin()
        coords_array = np.asarray(coords_array)
        return origin + sum(
            axis.number_to_point(coord) - origin
            for axis, coord in zip(axes, coords_array.T)
        )

    def c2p(self, *coords: float) -> np.ndarray:
        """:meth:`coords_to_point` 的缩写"""
        return self.coords_to_point(*coords)

    def point_to_coords3d(self, point: Vect | Iterable[Vect]) -> np.ndarray:
        """
        传入位置得到对应的坐标（但是会扩张为三维坐标；对于二维坐标系来说，第三个分量则表示距离二维平面的距离）

        也可以传入一组位置得到一组对应的坐标
        """
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
        """:meth:`point_to_coords3d` 的简写"""
        return self.point_to_coords3d(point)

    def point_to_coords(self, point: Vect | Iterable[Vect]) -> np.ndarray:
        """
        传入位置得到对应坐标

        也可以传入一组位置得到一组对应的坐标
        """
        axes = self.get_axes()
        return self.point_to_coords3d(point)[:len(axes)]

    def p2c(self, point: Vect | Iterable[Vect]) -> np.ndarray:
        """:meth:`point_to_coords` 的缩写"""
        return self.point_to_coords(point)

    def number_to_point(self, number: complex | float) -> np.ndarray:
        """传入复数得到对应位置"""
        number = complex(number)
        return self.coords_to_point(number.real, number.imag)

    def n2p(self, number: complex | float) -> np.ndarray:
        """:meth:`number_to_point` 的缩写"""
        return self.number_to_point(number)

    def point_to_number(self, point: Vect) -> complex:
        """传入位置得到对应复数"""
        x, y = self.point_to_coords3d(point)[:2]
        return complex(x, y)

    def p2n(self, point: Vect) -> complex:
        """:meth:`point_to_number` 的缩写"""
        return self.point_to_number(point)


class Axes(CoordinateSystem, MarkedItem, NamedGroupMixin, metaclass=_ItemMeta_ABCMeta):
    """
    二维坐标轴

    -   ``num_sampled_graph_points_per_tick``:

        表示 :meth:`get_graph` 方法在采样步长缺省时，在每段刻度中采样点的数量

    -   ``axis_config``:

        横坐标轴和纵坐标轴共用的配置项，可用参数请参考 :class:`~.NumberLine`

    -   ``x_axis_config``:

        横坐标轴的配置项，可用参数请参考 :class:`~.NumberLine`

    -   ``y_axis_config``:

        纵坐标轴的配置项，可用参数请参考 :class:`~.NumberLine`

    -   ``x_length``:

        当该值指定时，会将横坐标轴的长度拉伸以匹配该值

    -   ``y_length``:

        当该值指定时，会将纵坐标轴的长度拉伸以匹配该值

    -   ``unit_size``:

        指定横坐标与纵坐标的单位长度，如果指定了对应的 ``*_length`` 则会被忽略

        注：如果需要给某个坐标轴单独指定 ``unit_size``，请传入对应的 ``*_axis_config``
    """

    axis_config_d = dict(
        numbers_to_exclude=[0]
    )
    x_axis_config_d = {}
    y_axis_config_d = dict(
        line_to_number_direction=UP,
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
        x_length: float | None = None,
        y_length: float | None = None,
        height: float | None = None,
        width: float | None = None,
        unit_size: float = 1.0,
        **kwargs
    ):
        if height is not None:
            from janim.utils.deprecation import deprecated
            deprecated(
                'height',
                'y_length',
                remove=(4, 3)
            )
            y_length = height

        if width is not None:
            from janim.utils.deprecation import deprecated
            deprecated(
                'width',
                'x_length',
                remove=(4, 3)
            )
            x_length = width

        axis_config = dict(**axis_config, unit_size=unit_size)

        x_axis = CoordinateSystem.create_axis(
            x_range,
            axis_config=merge_dicts_recursively(
                self.axis_config_d,
                self.x_axis_config_d,
                axis_config,
                x_axis_config
            ),
            length=x_length
        )
        self.x_range = x_axis.x_range

        y_axis = CoordinateSystem.create_axis(
            y_range,
            axis_config=merge_dicts_recursively(
                self.axis_config_d,
                self.y_axis_config_d,
                axis_config,
                y_axis_config
            ),
            length=y_length
        )
        y_axis.points.rotate(90 * DEGREES, about_point=ORIGIN)
        self.y_range = y_axis.x_range

        super().__init__(
            named=dict(
                x_axis=x_axis,
                y_axis=y_axis,
            ),
            num_sampled_graph_points_per_tick=num_sampled_graph_points_per_tick,
            **kwargs
        )
        self.mark.set_points([ORIGIN])

    @property
    def x_axis(self) -> NumberLine:
        return self['x_axis']

    @property
    def y_axis(self) -> NumberLine:
        return self['y_axis']

    def get_axes(self) -> list[NumberLine]:
        return [self.x_axis, self.y_axis]

    def get_graph(
        self,
        function: Callable[[float], float],
        x_range: RangeSpecifier | None = None,
        *,
        bind: bool = True,
        **kwargs
    ) -> ParametricCurve:
        """
        基于坐标轴的坐标构造函数曲线，使用 :class:`~.ParametricCurve`

        -   ``function``: 用于构造曲线的函数

        -   ``x_range``: 图像定义域

            如果没有指定则使用横坐标的定义域

            指定时，可以使用 ``[x_min, x_max, x_step]`` 或者省略采样步长 ``[x_min, x_max]``

            如果没有指定采样步长，则将坐标轴的刻度步长除以物件的 ``num_sampled_graph_points_per_tick`` 作为采样步长

        -   ``bind``: 在默认情况下为 ``True``，会使得函数曲线自动同步应用于坐标系上的变换，也可同步动画，详见 :ref:`basic_examples` 中的 ``NumberPlaneExample``

        .. warning::

            当 ``bind=True`` 时，请勿将函数曲线与坐标系放在同一个 :class:`~.Group` 中进行坐标变换

            因为会导致变换效果被重复作用，（一次由 :class:`~.Group` 导致的作用，另一次由 ``bind=True`` 导致的作用）

            如果你有放在同一个 :class:`~.Group` 里的需求，请传入 ``bind=False`` 以避免该情况
        """
        t_range = self.x_range.copy()
        if x_range is not None:
            t_range[:len(x_range)] = x_range

        if x_range is None or len(x_range) < 3:
            # 当用户没有指定采样步长（没有指定 x_range 或者 x_range 不包含 step 的部分）时
            # 将 t_range[2] 除以 num_sampled_graph_points_per_tick，从刻度步长转换为采样步长
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
        t_range: tuple[float, float, float] = (0, 1, 0.1),
        *,
        bind: bool = True,
        **kwargs
    ):
        """
        基于坐标轴的坐标构造参数曲线，即 :class:`~.ParametricCurve`

        - ``function``: 将值映射为坐标系上的一个点的参数函数
        - ``bind``: 在默认情况下为 ``True``，会使得参数曲线自动同步应用于坐标系上的变换，也可同步动画，详见 :ref:`basic_examples` 中的 ``NumberPlaneExample``

        .. warning::

            当 ``bind=True`` 时，请勿将参数曲线与坐标系放在同一个 :class:`~.Group` 中进行坐标变换

            因为会导致变换效果被重复作用，（一次由 :class:`~.Group` 导致的作用，另一次由 ``bind=True`` 导致的作用）

            如果你有放在同一个 :class:`~.Group` 里的需求，请传入 ``bind=False`` 以避免该情况
        """
        graph = ParametricCurve(
            lambda t: self.coords_to_point(*function(t)),
            t_range,
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

    def get_area(
        self,
        graph: ParametricCurve,
        x_range: tuple[float, float] | None = None,
        color: JAnimColor = BLUE,
        alpha: float = 0.3,
        stroke_alpha: float | None = None,
        fill_alpha: float | None = None,
        bounded_graph: ParametricCurve = None,
        **kwargs
    ) -> Polygon:
        """
        构造 ``x_range`` 区间内，``graph`` 与坐标轴所围成的区域，使用 :class:`~.Polygon` 表示

        - ``graph``: 函数曲线，另见 :meth:`get_graph`
        - ``x_range``: ``x`` 区间的最小值与最大值，``x_range = [x_min, x_max]``
        - ``bounded_graph``: 如果指定该参数，那么将会构造 ``graph`` 与 ``bounded_graph`` 所围成的区域，而非与坐标轴
        """
        if x_range is None:
            a, b, _ = graph.t_range
        else:
            a, b = x_range

        if bounded_graph is None:
            points = [
                self.c2p(a),
                graph.t_func(a),
                *[p for p in graph.points.get_anchors() if a < self.p2c(p)[0] < b],
                graph.t_func(b),
                self.c2p(b)
            ]
        else:
            graph_points, bounded_graph_points = (
                [
                    g.t_func(a),
                    *[p for p in g.points.get_anchors() if a < self.p2c(p)[0] < b],
                    g.t_func(b)
                ]
                for g in (graph, bounded_graph)
            )
            points = graph_points + bounded_graph_points[::-1]

        return Polygon(
            *points,
            color=color,
            alpha=alpha,
            stroke_alpha=stroke_alpha,
            fill_alpha=fill_alpha,
            **kwargs
        )

    def get_axis_labels(
        self,
        x_label: str | Points = 'x',
        y_label: str | Points = 'y',
        x_kwargs: dict = {},
        y_kwargs: dict = {},
        **kwargs,
    ) -> Group[TypstMath | Points]:
        """
        详见 :meth:`~.NumberLine.get_axis_label`

        如果设置 ``ensure_on_screen=True``，坐标轴标签会自动调整位置移动到默认屏幕区域内
        """
        return Group(
            self.get_x_axis_label(x_label, **x_kwargs, **kwargs),
            self.get_y_axis_label(y_label, **y_kwargs, **kwargs),
        )

    def get_x_axis_label(
        self,
        label: str | Points = 'x',
        **kwargs
    ) -> TypstMath | Points:
        """
        详见 :meth:`~.NumberLine.get_axis_label`

        如果设置 ``ensure_on_screen=True``，坐标轴标签会自动调整位置移动到默认屏幕区域内
        """
        return self.x_axis.get_axis_label(label, **kwargs)

    def get_y_axis_label(
        self,
        label: str | Points = 'y',
        **kwargs
    ) -> TypstMath | Points:
        """
        详见 :meth:`~.NumberLine.get_axis_label`

        如果设置 ``ensure_on_screen=True``，坐标轴标签会自动调整位置移动到默认屏幕区域内
        """
        return self.y_axis.get_axis_label(label, **kwargs)


class ThreeDAxes(Axes):
    """
    三维坐标轴

    - ``z_normal`` 表示 z 坐标轴上刻度和箭头标记的面向，默认面向 ``UP`` 方向

    其它可用参数请参考并类比 :class:`Axes` 的使用
    """
    z_axis_config_d = {}

    def __init__(
        self,
        x_range: RangeSpecifier = (-6, 6, 1),
        y_range: RangeSpecifier = (-5, 5, 1),
        z_range: RangeSpecifier = (-4, 4, 1),
        *,
        axis_config: dict = {},
        z_length: float | None = None,
        z_axis_config: dict = {},
        z_normal: Vect = UP,
        **kwargs
    ):
        super().__init__(x_range, y_range, axis_config=axis_config, **kwargs)
        self.z_normal_angle = angle_of_vector(z_normal)

        z_axis = CoordinateSystem.create_axis(
            z_range,
            axis_config=merge_dicts_recursively(
                self.axis_config_d,
                self.z_axis_config_d,
                axis_config,
                z_axis_config
            ),
            length=z_length
        )
        z_axis.points \
            .rotate(-PI / 2, axis=UP, about_point=ORIGIN) \
            .rotate(self.z_normal_angle - PI, axis=OUT, about_point=ORIGIN) \
            .shift(self.x_axis.mark.get())
        self.z_range = z_axis.x_range

        self.add(z_axis=z_axis)

    @property
    def z_axis(self) -> NumberLine:
        return self['z_axis']

    def get_axes(self) -> list[NumberLine]:
        return [*super().get_axes(), self.z_axis]

    def get_axis_labels(
        self,
        x_label: str | Points = 'x',
        y_label: str | Points = 'y',
        z_label: str | Points = 'z',
        x_kwargs: dict = {},
        y_kwargs: dict = {},
        z_kwargs: dict = {},
        rotate_xy: bool = True,
        z_point_up: bool = True,
        **kwargs,
    ) -> Group[TypstMath | Points]:
        """
        详见 :meth:`~.NumberLine.get_axis_label`

        另外，在默认情况下 ``rotate_xy=True`` 会将 x、y 轴的标签原地旋转半圈，以匹配从 x、y、z 三个轴的正方向看向原点的视角

        以及，直接生成的 z 坐标轴标签会和 2D 平面平行，默认情况下 ``point_up=True`` 会将其立起来和 z 轴方向一致，传入 ``point_up=False`` 可禁用该行为
        """
        x_axis_label = self.get_x_axis_label(x_label, **x_kwargs, **kwargs)
        y_axis_label = self.get_y_axis_label(y_label, **y_kwargs, **kwargs)
        z_axis_label = self.get_z_axis_label(z_label, z_point_up, **z_kwargs, **kwargs)

        if rotate_xy:
            for label in (x_axis_label, y_axis_label):
                label.points.rotate(PI)

        return Group(x_axis_label, y_axis_label, z_axis_label)

    def get_z_axis_label(
        self,
        label: str | Points = 'z',
        point_up: bool = True,
        **kwargs
    ) -> TypstMath | Points:
        """
        详见 :meth:`~.NumberLine.get_axis_label`

        另外，直接生成的坐标轴标签会和 2D 平面平行，默认情况下 ``point_up=True`` 会将其立起来和 z 轴方向一致，传入 ``point_up=False`` 可禁用该行为
        """
        label = self.z_axis.get_axis_label(label, **kwargs)
        if point_up:
            axis_end = self.z_axis.points.get_end()
            label.points \
                .rotate(PI / 2, axis=RIGHT, about_point=axis_end) \
                .rotate(self.z_normal_angle + PI / 2, about_point=axis_end)
        return label


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
    """
    坐标网格

    一般来说包含：

    -   坐标轴：

        默认是白色的坐标轴，不带箭头标志和刻度线

    -   主要网格线：

        颜色默认是 BLUE_D，可传入 ``background_line_style`` 调整

    -   次要网格线：

        -   可使用 ``faded_line_style`` 调整

            当 ``faded_line_style`` 没有设置时，会将采用与 ``background_line_style`` 相同的配置，并将其颜色透明化 50% 来使用

        -   使用 ``faded_line_ratio`` 调整每个网格中次要网格线的数量

            例如默认的 ``4`` 表示每两个主要网格线之间等距排布了 4 个次要网格线

            可调整成 ``1``，减少次要网格线的密集程度，或是直接设置成 ``0`` 来禁用次要网格线

    更多参数与方法另请参考 :class:`Axes`
    """

    points = CmptInfo(CmptVPoints_NumberPlaneImpl)

    background_line_style_d = dict(
        stroke_color=BLUE_D,
        stroke_radius=0.01,
    )
    axis_config_d = dict(
        stroke_color=WHITE,
        stroke_radius=0.01,
        include_ticks=False,
        include_tip=False,
        line_to_number_buff=SMALL_BUFF,
        line_to_number_direction=DL
    )
    y_axis_config_d = dict(
        line_to_number_direction=DL,
        numbers_to_exclude=[0]
    )

    def __init__(
        self,
        x_range: RangeSpecifier = DEFAULT_X_RANGE,
        y_range: RangeSpecifier = DEFAULT_Y_RANGE,
        background_line_style: dict = {},
        # Defaults to a faded version of line_config
        faded_line_style: dict = {},
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
            prepend=True
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
        inputs = NumberLine.compute_tick_range(axis2.x_min, axis2.x_max, step)

        if len(inputs) == 0:  # 为了 inputs[0] 的有效性
            return lines1, lines2

        # 因为 inputs 的起始位置并不总是 not-faded line，所以这里要计算出 i 的偏移量
        i_offset = round(inputs[0] / step)

        for i, x in enumerate(inputs):
            if abs(x) < 1e-8:
                continue
            new_line = line.copy()
            new_line.points.shift(axis2.n2p(x) - axis2.n2p(0))
            if (i_offset + i) % (1 + ratio) == 0:
                lines1.add(new_line)
            else:
                lines2.add(new_line)

        return lines1, lines2
