import itertools as it
from typing import Any, Callable, Iterable, Literal, Self, Sequence, overload

import numpy as np

from janim.components.component import CmptInfo
from janim.components.points import Cmpt_Points
from janim.constants import BLUE_D, BLUE_E, GREY_A, GREY_B
from janim.items.geometry.polygon import Polygon
from janim.items.group import Group
from janim.items.item import Item
from janim.items.points import DotCloud, Points
from janim.items.vitem import VItem
from janim.render.renderer_smooth_surface import SmoothSurfaceRenderer
from janim.typing import ColorArray, JAnimColor, Vect
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
    def __init__(self, geometry: T, resolution: Resolution | None = None, **kwargs):
        self.geometry = geometry
        self.resolution = geometry.resolve_resolution('smooth', resolution)

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
    }

    def __init__(
        self,
        uv_func: Callable[[float, float], Vect],
        u_range: tuple[float, float],
        v_range: tuple[float, float],
        **kwargs
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
