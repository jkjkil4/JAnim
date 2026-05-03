from __future__ import annotations

import itertools as it
from typing import Any, Callable, Iterable, Literal, Self, overload

import numpy as np

from janim.components.component import CmptInfo
from janim.components.points import Cmpt_Points
from janim.components.rgba import Cmpt_Rgba
from janim.components.rgbas import Cmpt_Rgbas
from janim.constants import BLUE_D, BLUE_E, GREY_A, GREY_B
from janim.items.geometry.polygon import Polygon
from janim.items.group import Group
from janim.items.item import Item
from janim.items.points import DotCloud, Points
from janim.items.vitem import VItem
from janim.locale import get_translator
from janim.render.renderer_smooth_surface import SmoothSurfaceRenderer
from janim.render.renderer_checkerboard_surface import CheckerboardSurfaceRenderer
from janim.typing import ColorArray, JAnimColor, RgbaArray, Vect
from janim.utils.data import AlignedData, Array
from janim.utils.dict_ops import merge_dicts_recursively
from janim.utils.iterables import resize_preserving_order

_ = get_translator('janim.items.three_d.types')

type Resolution = int | tuple[int, int]


def _unpack_resolution(resolution: Resolution) -> tuple[int, int]:
    if isinstance(resolution, int):
        return resolution, resolution
    return resolution


def _get_u_values_and_v_values(
    u_range: tuple[float, float],
    v_range: tuple[float, float],
    resolution: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    u_res, v_res = resolution
    u_values = np.linspace(*u_range, u_res + 1)
    v_values = np.linspace(*v_range, v_res + 1)
    return u_values, v_values


class SurfaceFace(Polygon):
    def __init__(
        self, u1: float, u2: float, v1: float, v2: float, u_index: int, v_index: int, **kwargs
    ):
        super().__init__(
            [u1, v1, 0],
            [u2, v1, 0],
            [u2, v2, 0],
            [u1, v2, 0],
            **kwargs,
        )
        self.uuvv = (u1, u2, v1, v2)
        self.u_index = u_index
        self.v_index = v_index


# region 各种 Surface 类型


class NormSurface[T: SurfaceGeometry](Points):
    """
    :class:`CheckerboardSurface` 和 :class:`SmoothSurface` 的基类

    提供了对 ``du_points`` 和 ``dv_points`` 的封装，以便计算法向量
    """

    _du_points = CmptInfo(Cmpt_Points[Self])
    _dv_points = CmptInfo(Cmpt_Points[Self])

    resolution_type: str | None = None

    def __init__(
        self,
        geometry: T,
        resolution: Resolution | None = None,
        epsilon: float = 1e-3,
        **kwargs,
    ):
        assert self.resolution_type is not None

        self.geometry = geometry
        self.resolution = geometry.resolve_resolution(self.resolution_type, resolution)
        self.epsilon = epsilon

        super().__init__(**kwargs)
        self._update_resolution(self.resolution)

        self.apply_depth_test()

    def init_connect(self) -> None:
        super().init_connect()
        Cmpt_Points.apply_points_fn.connect(self.points, self._on_points_transformed)

    def _on_points_transformed(self, func, about_point) -> None:
        self._du_points.apply_points_fn(func, about_point=about_point, about_edge=None)
        self._dv_points.apply_points_fn(func, about_point=about_point, about_edge=None)

    def _update_resolution(self, resolution: tuple[int, int]) -> None:
        self.resolution = resolution

        points, du_points, dv_points = self._get_points_and_dpoints()
        self.points.set(points)
        self._du_points.set(du_points)
        self._dv_points.set(dv_points)

        self._tri_indices = self._get_tri_indices()

    def _get_points_and_dpoints(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        u_values, v_values = _get_u_values_and_v_values(
            self.geometry.u_range, self.geometry.v_range, self.resolution
        )
        U, V = np.meshgrid(u_values, v_values, indexing='ij')
        uv_grid = np.stack([U, V], axis=-1)
        uv_plus_du = uv_grid.copy()
        uv_plus_du[:, :, 0] += self.epsilon
        uv_plus_dv = uv_grid.copy()
        uv_plus_dv[:, :, 1] += self.epsilon

        uv_func = self.geometry.uv_func
        points, du_points, dv_points = [
            np.array(
                [
                    uv_func(u, v)  #
                    for u, v in grid.reshape(-1, 2)
                ]
            )
            for grid in (uv_grid, uv_plus_du, uv_plus_dv)
        ]
        return points, du_points, dv_points

    def _get_tri_indices(self) -> np.ndarray:
        res_u, res_v = self.resolution
        idx = np.arange((res_u + 1) * (res_v + 1)).reshape((res_u + 1, res_v + 1))
        p0 = idx[:-1, :-1].ravel()
        p1 = idx[1:, :-1].ravel()
        p2 = idx[:-1, 1:].ravel()
        p3 = idx[1:, 1:].ravel()
        # 组装三角形索引
        indices = np.stack([p0, p1, p2, p1, p3, p2], axis=1)
        return indices.astype('i4')

    @classmethod
    def align_for_interpolate(cls, item1: Item, item2: Item) -> AlignedData[Self]:
        """
        依照 uv 网格对齐采样分辨率以及三角形索引，而不是像原先一样简单逐点对齐
        """
        assert isinstance(item1, NormSurface) and isinstance(item2, NormSurface)

        res1_u, res1_v = item1.resolution
        res2_u, res2_v = item2.resolution

        res_u, res_v = res = max(res1_u, res2_u), max(res1_v, res2_v)
        needs_resample1 = res1_u != res_u or res1_v != res_v
        needs_resample2 = res2_u != res_u or res2_v != res_v

        aligned = super().align_for_interpolate(item1, item2)

        if needs_resample1:
            aligned.data1._update_resolution(res)
            # 因为在内部 union 是从 data1 复制来的，所以这里只需要在 needs_resample1 时更新 union 的
            aligned.union._tri_indices = aligned.data1._tri_indices
        if needs_resample2:
            aligned.data2._update_resolution(res)

        return aligned


class CheckerboardSurface[T: SurfaceGeometry](NormSurface[T]):
    """
    棋盘格样式的曲面，默认着色为蓝色深浅交替网格

    .. note::

        该样式的曲面在半透明情况下的表现有待完善

    .. note::

        该样式的曲面作为整体渲染，因此无法将每个面作为单独的物件进行操作

        对于每个面以独立物件存在的形式，请参考 :class:`CheckerboardSurface`

    :param geometry: 由 :meth:`SurfaceGeometry.into` 自动提供
    :param resolution: 覆盖默认分辨率设置，可传入单个值或者传入一对值来表示在 ``u`` 和 ``v`` 方向的分辨率
    :param checkerboard_colors: 棋盘格颜色列表，会对网格循环使用其中的颜色
    """

    resolution_type = 'face'

    class _Cmpt_SurfaceRgbas[ItemT](Cmpt_Rgbas[ItemT], impl=True):
        def set_rgbas(self, rgbas: RgbaArray) -> Self:
            rgbas = np.asarray(rgbas)
            assert len(rgbas) == 2
            return super().set_rgbas(rgbas)

    color = CmptInfo(_Cmpt_SurfaceRgbas[Self])

    renderer_cls = CheckerboardSurfaceRenderer

    def __init__(
        self,
        geometry: T,
        resolution: Resolution | None = None,
        checkerboard_colors: ColorArray = [BLUE_D, BLUE_E],
        alpha: float = 1.0,
        epsilon: float = 1e-3,
        **kwargs,
    ):
        super().__init__(geometry, resolution, epsilon, **kwargs)
        self.color.set(checkerboard_colors, alpha)

    def apply_style(
        self,
        color: JAnimColor | ColorArray | None = None,
        alpha: float | None = None,
        **kwargs,
    ) -> Self:
        if color is None or alpha is not None:
            self.color.set(color, alpha)

        super().apply_style(**kwargs)
        return self


class VCheckerboardSurface[T: SurfaceGeometry](Group[SurfaceFace], VItem):
    """
    棋盘格样式的曲面，默认着色为蓝色深浅交替网格

    .. warning::

        由于该样式的曲面的每个网格面都是独立的 :class:`~.VItem` 物件，因此性能普遍较差

        对于性能较优的方式，请参考 :class:`CheckerboardSurface`

    :param geometry: 由 :meth:`SurfaceGeometry.into` 自动提供
    :param resolution: 覆盖默认分辨率设置，可传入单个值或者传入一对值来表示在 ``u`` 和 ``v`` 方向的分辨率
    :param checkerboard_colors: 棋盘格颜色列表，会对网格循环使用其中的颜色
    :param stroke_color: 网格边线颜色
    :param stroke_radius: 网格边线粗细
    """

    def __init__(
        self,
        geometry: T,
        resolution: Resolution | None = None,
        fill_color: JAnimColor | None = None,
        fill_alpha: float = 1.0,
        checkerboard_colors: ColorArray = [BLUE_D, BLUE_E],
        stroke_color: JAnimColor = GREY_B,
        stroke_radius: float = 0.0025,
        should_make_jagged: bool = False,
        **kwargs,
    ):
        self.geometry = geometry
        self.resolution = geometry.resolve_resolution('face', resolution)

        super().__init__(
            *self._get_uv_faces(),
            fill_alpha=fill_alpha,
            stroke_color=stroke_color,
            stroke_radius=stroke_radius,
            **kwargs,
        )
        if fill_color is not None:
            self.set(fill_color=fill_color)
        else:
            self.set_fill_by_checkerboard(*checkerboard_colors)

        self.points.apply_point_fn(lambda p: self.geometry.uv_func(p[0], p[1]))
        if should_make_jagged:
            self.points.make_jagged()

        self.apply_distance_sort().shade_in_3d()

    def _get_uv_faces(self) -> list[SurfaceFace]:
        u_values, v_values = _get_u_values_and_v_values(
            self.geometry.u_range, self.geometry.v_range, self.resolution
        )
        return [
            SurfaceFace(u1, u2, v1, v2, i, j)
            for i, (u1, u2) in enumerate(it.pairwise(u_values))
            for j, (v1, v2) in enumerate(it.pairwise(v_values))
        ]

    def set_fill_by_checkerboard(self, *colors: JAnimColor, alpha: float | None = None) -> Self:
        """
        以棋盘网格的样式设置填充色

        :param colors: 用于交替填充的颜色序列（按顺序循环使用），例如只有两个颜色时即为经典的棋盘网格样式
        :param alpha: 填充透明度；若为 ``None`` 则保持当前透明度不变
        """
        n_colors = len(colors)
        for face in self:
            c_index = (face.u_index + face.v_index) % n_colors
            face.fill.set(colors[c_index], alpha)
        return self

    # TODO: set_fill_by_value

    @classmethod
    def align_for_interpolate(
        cls, item1: CheckerboardSurface, item2: CheckerboardSurface
    ) -> AlignedData[Self]:
        """
        依照 uv 网格对齐棋盘格物件，而不是像原先一样简单逐个对齐
        """
        aligned = super().align_for_interpolate(item1, item2)

        item1_grid = item1.get_children_in_grid()
        item2_grid = item2.get_children_in_grid()

        # 先在 u 方向对齐
        max_len = max(len(item1_grid), len(item2_grid))
        item1_grid = resize_preserving_order(item1_grid, max_len)
        item2_grid = resize_preserving_order(item2_grid, max_len)

        # 然后在 v 方向对齐
        for row1, row2 in zip(item1_grid, item2_grid, strict=True):
            max_len = max(len(row1), len(row2))
            row1[:] = resize_preserving_order(row1, max_len)
            row2[:] = resize_preserving_order(row2, max_len)

        aligned.data1._stored_children = list(it.chain(*item1_grid))
        aligned.data2._stored_children = list(it.chain(*item2_grid))

        return aligned

    def get_children_in_grid(self) -> list[list[SurfaceFace]]:
        """
        得到棋盘格二维数组，``v`` 主序
        """
        batched = it.batched(self.get_children(), self.resolution[1], strict=True)
        return [list(row) for row in batched]


class WireframeSurface[T: SurfaceGeometry](Group[VItem], VItem):
    """
    线框样式的曲面

    .. warning::

        由于该样式的曲面的每个线框都是独立的 :class:`~.VItem` 物件，因此性能普遍较差

    :param geometry: 由 :meth:`SurfaceGeometry.into` 自动提供
    :param resolution: 覆盖默认分辨率设置，可传入单个值或者传入一对值来表示在 ``u`` 和 ``v`` 方向的分辨率
    :param stroke_color: 线框颜色
    :param stroke_radius: 线框粗细
    """

    def __init__(
        self,
        geometry: T,
        resolution: Resolution | None = None,
        stroke_color: JAnimColor = GREY_A,
        stroke_radius: float = 0.005,
        depth_test: bool = False,
        should_make_smooth: bool = True,
        **kwargs,
    ):
        self.geometry = geometry
        self.resolution = geometry.resolve_resolution('face', resolution)
        self.resolution: tuple[int, int] = tuple(
            (res if res % 2 == 0 else res + 1) for res in self.resolution
        )  # type: ignore

        super().__init__(
            *self._get_uv_lines(),
            stroke_radius=stroke_radius,
            stroke_color=stroke_color,
            **kwargs,
        )
        if depth_test:
            self.apply_depth_test()
        if should_make_smooth:
            self.points.make_smooth(approx=True)

    def _get_uv_lines(self) -> list[VItem]:
        u_values, v_values = _get_u_values_and_v_values(
            self.geometry.u_range, self.geometry.v_range, self.resolution
        )

        u_lines = [
            VItem(*[self.geometry.uv_func(u, v) for v in v_values])  #
            for u in u_values
        ]
        v_lines = [
            VItem(*[self.geometry.uv_func(u, v) for u in u_values])  #
            for v in v_values
        ]

        return [*u_lines, *v_lines]

    @classmethod
    def align_for_interpolate(
        cls, item1: WireframeSurface, item2: WireframeSurface
    ) -> AlignedData[Self]:
        """
        依照 uv 网格对齐线框，而不是像原先一样简单逐个对齐
        """
        aligned = super().align_for_interpolate(item1, item2)

        res1_u, res1_v = item1.resolution
        res2_u, res2_v = item2.resolution
        item1_children = item1.get_children()
        item2_children = item2.get_children()
        assert len(item1_children) == res1_u + res1_v + 2
        assert len(item2_children) == res2_u + res2_v + 2

        def align_lines(
            lines1: list[VItem], lines2: list[VItem]
        ) -> tuple[list[VItem], list[VItem]]:
            max_len = max(len(lines1), len(lines2))
            return (
                resize_preserving_order(lines1, max_len),
                resize_preserving_order(lines2, max_len),
            )

        u_lines1, u_lines2 = align_lines(
            item1_children[: res1_u + 1],
            item2_children[: res2_u + 1],
        )
        v_lines1, v_lines2 = align_lines(
            item1_children[-res1_v - 1 :],
            item2_children[-res2_v - 1 :],
        )

        aligned.data1._stored_children = [*u_lines1, *v_lines1]
        aligned.data2._stored_children = [*u_lines2, *v_lines2]

        return aligned


class SmoothSurface[T: SurfaceGeometry](NormSurface[T]):
    """
    平滑表面样式的曲面

    .. note::

        该样式的曲面在半透明情况下的表现有待完善

    :param geometry: 由 :meth:`SurfaceGeometry.into` 自动提供
    :param resolution: 覆盖默认分辨率设置，可传入单个值或者传入一对值来表示在 ``u`` 和 ``v`` 方向的分辨率
    """

    resolution_type = 'smooth'

    class Cmpt_SurfaceRgba[ItemT](Cmpt_Rgba[ItemT], impl=True):
        DEFAULT_RGBA_ARRAY = Array.create([0.53, 0.53, 0.53, 1.0])  # GREY_C

    color = CmptInfo(Cmpt_SurfaceRgba[Self])

    renderer_cls = SmoothSurfaceRenderer

    def apply_style(
        self,
        color: JAnimColor | None = None,
        alpha: float | None = None,
        **kwargs,
    ) -> Self:
        if color is not None or alpha is not None:
            self.color.set(color, alpha)

        super().apply_style(**kwargs)
        return self


class DotCloudSurface[T: SurfaceGeometry](DotCloud):
    def __init__(
        self,
        geometry: T,
        resolution: Resolution | None = None,
        radius: float | Iterable[float] = 0.01,
        **kwargs,
    ):
        self.geometry = geometry
        self.resolution = geometry.resolve_resolution('smooth', resolution)

        super().__init__(*self._get_dot_points(), radius=radius, **kwargs)

    def _get_dot_points(self) -> np.ndarray:
        u_values, v_values = _get_u_values_and_v_values(
            self.geometry.u_range, self.geometry.v_range, self.resolution
        )
        uv_func = self.geometry.uv_func
        return np.array([uv_func(u, v) for u in u_values for v in v_values])

    def get_points_in_grid(self) -> np.ndarray:
        """
        得到点集二维数组，``v`` 主序
        """
        return self.points.get().reshape(-1, (self.resolution[1] + 1), 3)

    @classmethod
    def align_for_interpolate(
        cls, item1: DotCloudSurface, item2: DotCloudSurface
    ) -> AlignedData[DotCloud]:
        """
        依照 uv 网格对齐点，而不是像原先一样简单逐点对齐
        """
        aligned = super().align_for_interpolate(item1, item2)

        item1_grid = item1.get_points_in_grid().copy()
        item2_grid = item2.get_points_in_grid().copy()

        len1_u, len1_v, _ = item1_grid.shape
        len2_u, len2_v, _ = item2_grid.shape

        len_u, len_v = max(len1_u, len2_u), max(len1_v, len2_v)
        indices1_u = np.arange(len_u) * len1_u // len_u
        indices1_v = np.arange(len_v) * len1_v // len_v
        indices2_u = np.arange(len_u) * len2_u // len_u
        indices2_v = np.arange(len_v) * len2_v // len_v

        aligned1 = item1_grid[np.ix_(indices1_u, indices1_v)]
        aligned2 = item2_grid[np.ix_(indices2_u, indices2_v)]

        aligned.data1.points.set(aligned1.reshape(-1, 3))
        aligned.data2.points.set(aligned2.reshape(-1, 3))

        return aligned


# endregion


class SurfaceGeometry:
    RESOLUTIONS: dict[str, Resolution] = {
        'face': 32,
        'smooth': 101,
    }

    SURFACE_TYPES: dict[str, Any] = {
        'checker': CheckerboardSurface,
        'vchecker': VCheckerboardSurface,
        'wire': WireframeSurface,
        'smooth': SmoothSurface,
        'dots': DotCloudSurface,
    }

    def __init__(
        self,
        uv_func: Callable[[float, float], Vect],
        u_range: tuple[float, float],
        v_range: tuple[float, float],
        **kwargs,
    ):
        self.uv_func = uv_func
        self.u_range = u_range
        self.v_range = v_range

        self.kwargs = kwargs

    @overload
    def into(self, mode: Literal['checker'], **kwargs) -> CheckerboardSurface[Self]:
        """
        棋盘格样式的曲面，默认着色为蓝色深浅网格

        具体文档请参考 :class:`CheckerboardSurface`
        """

    @overload
    def into(self, mode: Literal['vchecker'], **kwargs) -> VCheckerboardSurface[Self]:
        """
        棋盘格样式的曲面，默认着色为蓝色深浅网格

        .. warning::

            由于该样式的曲面的每个网格面都是独立的 :class:`~.VItem` 物件，因此性能普遍较差

        具体文档请参考 :class:`VCheckerboardSurface`
        """

    @overload
    def into(self, mode: Literal['wire'], **kwargs) -> WireframeSurface[Self]:
        """
        线框样式的曲面

        .. warning::

            由于该样式的曲面的每个线框都是独立的 :class:`~.VItem` 物件，因此性能普遍较差

        具体文档请参考 :class:`WireframeSurface`
        """

    @overload
    def into(self, mode: Literal['smooth'], **kwargs) -> SmoothSurface[Self]:
        """
        平滑表面样式的曲面

        .. note::

            该样式的曲面在半透明情况下的表现有待完善

        具体文档请参考 :class:`SmoothSurface`
        """

    @overload
    def into(self, mode: Literal['dots'], **kwargs) -> DotCloudSurface[Self]:
        """
        点集样式的曲面
        """

    @overload
    def into[T: Item](self, mode: type[T], **kwargs) -> T:
        """
        指定一个类来构造自定义的曲面样式

        具体可参考 :class:`VCheckerboardSurface` :class:`WireframeSurface` :class:`SmoothSurface` 内置类的实现，
        应至少接受一个 ``geometry`` 参数
        """

    def into(self, mode, **kwargs):
        merged_kwargs = merge_dicts_recursively(self.kwargs, kwargs)

        if isinstance(mode, str):
            return self.SURFACE_TYPES[mode](self, **merged_kwargs)
        return mode(self, **merged_kwargs)

    def resolve_resolution(self, type: str, override: Resolution | None) -> tuple[int, int]:
        if override is None:
            resolution = self.RESOLUTIONS[type]
        else:
            resolution = override
        return _unpack_resolution(resolution)
