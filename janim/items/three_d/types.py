from __future__ import annotations

import itertools as it
from typing import Any, Callable, Literal, Self, overload

import numpy as np

from janim.components.component import CmptInfo
from janim.components.points import Cmpt_Points
from janim.components.rgba import Cmpt_Rgba
from janim.constants import BLUE_D, BLUE_E, GREY_A, GREY_B
from janim.items.geometry.polygon import Polygon
from janim.items.group import Group
from janim.items.item import Item
from janim.items.points import Points
from janim.items.vitem import VItem
from janim.render.renderer_smooth_surface import SmoothSurfaceRenderer
from janim.typing import ColorArray, JAnimColor, Vect
from janim.utils.data import AlignedData, Array
from janim.utils.dict_ops import merge_dicts_recursively

type Resolution = int | tuple[int, int]


def _unpack_resolution(resolution: Resolution) -> tuple[int, int]:
    if isinstance(resolution, int):
        return resolution, resolution
    return resolution


def _get_u_values_and_v_values(
    u_range: tuple[float, float],
    v_range: tuple[float, float],
    resolution: Resolution,
) -> tuple[np.ndarray, np.ndarray]:
    u_res, v_res = _unpack_resolution(resolution)
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


# region 三大 Surface 类型


class CheckerboardSurface[T: SurfaceGeometry](Group[SurfaceFace], VItem):
    # TODO: docstring
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


class WireframeSurface[T: SurfaceGeometry](Group[VItem], VItem):
    def __init__(
        self,
        geometry: T,
        resolution: Resolution | None = None,
        stroke_radius: float = 0.005,
        stroke_color: JAnimColor = GREY_A,
        depth_test: bool = False,
        should_make_smooth: bool = True,
        **kwargs,
    ):
        self.geometry = geometry
        self.resolution = geometry.resolve_resolution('face', resolution)

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


class SmoothSurface[T: SurfaceGeometry](Points):
    _du_points = CmptInfo(Cmpt_Points[Self])
    _dv_points = CmptInfo(Cmpt_Points[Self])

    class Cmpt_SurfaceRgba[ItemT](Cmpt_Rgba[ItemT], impl=True):
        DEFAULT_RGBA_ARRAY = Array.create([0.53, 0.53, 0.53, 1.0])  # GREY_C

    color = CmptInfo(Cmpt_SurfaceRgba[Self])

    renderer_cls = SmoothSurfaceRenderer

    def __init__(
        self, geometry: T, resolution: Resolution | None = None, epsilon: float = 1e-3, **kwargs
    ):
        self.geometry = geometry
        self.resolution = geometry.resolve_resolution('smooth', resolution)
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

    def _update_resolution(self, resolution: Resolution) -> None:
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
        res_u, res_v = _unpack_resolution(self.resolution)
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
        对齐 uv 网格采样分辨率以及三角形索引，而不是像原先一样简单逐点对齐
        """
        assert isinstance(item1, SmoothSurface) and isinstance(item2, SmoothSurface)

        res1_u, res1_v = _unpack_resolution(item1.resolution)
        res2_u, res2_v = _unpack_resolution(item2.resolution)

        res_u, res_v = res = max(res1_u, res2_u), max(res1_v, res2_v)
        needs_resample1 = res1_u != res_u or res1_v != res_v
        needs_resample2 = res2_u != res_u or res2_v != res_v

        aligned = super().align_for_interpolate(item1, item2)

        if needs_resample1:
            aligned.data1._update_resolution(res)
            # 因为在内部 union 是从 data1 复制来的，所以这里只需要在 needs_resample1 时更新 union 的 indices
            aligned.union._tri_indices = aligned.data1._tri_indices
        if needs_resample2:
            aligned.data2._update_resolution(res)

        return aligned


# class DotCloudSurface[T: SurfaceGeometry](DotCloud):
#     def __init__(
#         self,
#         geometry: T,
#         resolution: Resolution | None = None,
#         radius: float | Iterable[float] = 0.01,
#
#         **kwargs,
#     ):
#         self.geometry = geometry
#         self.resolution = geometry.resolve_resolution('smooth', resolution)
#
#         super().__init__(*self._get_dot_points(), radius=radius, **kwargs)
#
#     def _get_dot_points(self) -> np.ndarray:
#         u_values, v_values = _get_u_values_and_v_values(
#             self.geometry.u_range, self.geometry.v_range, self.resolution
#         )
#         uv_func = self.geometry.uv_func
#         return np.array([uv_func(u, v) for u in u_values for v in v_values])


# endregion


class SurfaceGeometry:
    RESOLUTIONS: dict[str, Resolution] = {
        'face': 32,
        'smooth': 101,
    }

    SURFACE_TYPES: dict[str, Any] = {
        'checker': CheckerboardSurface,
        'wire': WireframeSurface,
        'smooth': SmoothSurface,
        # 'dots': DotCloudSurface,
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
    def into(self, mode: Literal['checker'], **kwargs) -> CheckerboardSurface[Self]: ...
    @overload
    def into(self, mode: Literal['wire'], **kwargs) -> WireframeSurface[Self]: ...
    @overload
    def into(self, mode: Literal['smooth'], **kwargs) -> SmoothSurface[Self]: ...
    # @overload
    # def into(self, mode: Literal['dots'], **kwargs) -> DotCloudSurface[Self]: ...
    @overload
    def into[T: Item](self, mode: type[T], **kwargs) -> T: ...

    def into(self, mode, **kwargs):
        merged_kwargs = merge_dicts_recursively(self.kwargs, kwargs)

        if isinstance(mode, str):
            return self.SURFACE_TYPES[mode](self, **merged_kwargs)
        return mode(self, **merged_kwargs)

    def resolve_resolution(self, type: str, override: Resolution | None) -> Resolution:
        if override is not None:
            return override
        return self.RESOLUTIONS[type]
