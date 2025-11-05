from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from janim.camera.camera_info import CameraInfo
from janim.constants import NAN_POINT
from janim.render.base import RenderData, Renderer
from janim.render.program import (get_compute_shader_from_file,
                                  get_program_from_file_prefix)

if TYPE_CHECKING:
    from janim.items.vitem import VItem


class VItemCurveRenderer(Renderer):
    '''
    对于纯曲线边界 :class:`~.VItem` 所使用的渲染器
    '''

    shader_path_compatibility = 'render/shaders/vitem/vitem_curve_compatibility'
    shader_path_normal = 'render/shaders/vitem/vitem_curve'

    def __init__(self):
        self.initialized = False

    def render(self, item: VItem) -> None:
        self.ctx = self.data_ctx.get().ctx
        compatibility = self.ctx.version_code < 430

        if compatibility:
            self.render = self.render_compatibility
        else:
            self.render = self.render_normal

        self.render(item)

    # region init

    def init_compatibility(self) -> None:
        self.prog = get_program_from_file_prefix(self.shader_path_compatibility)
        self.init_common()

        # TODO
        raise NotImplementedError()

    def init_normal(self) -> None:
        self.prog = get_program_from_file_prefix(self.shader_path_normal)
        self.init_common()

        self.comp = get_compute_shader_from_file('render/shaders/map_points.comp.glsl')
        self.comp_u_fix = self.get_u_fix_in_frame(self.comp)
        self.vbo_points = self.ctx.buffer(reserve=1)

    @dataclass(slots=True)
    class RenderAttrs:
        camera_info: CameraInfo | None = None

        fix_in_frame: bool | None = None
        points: np.ndarray | None = None
        radius: np.ndarray | None = None
        stroke: np.ndarray | None = None
        fill: np.ndarray | None = None
        glow_size: float | None = None
        glow_visible: bool | None = None

        @staticmethod
        def get(render_data: RenderData, item: VItem) -> VItemCurveRenderer.RenderAttrs:
            return VItemCurveRenderer.RenderAttrs(
                render_data.camera_info,
                item._fix_in_frame,
                item.points._points._data,
                item.radius._radii._data,
                item.stroke._rgbas._data,
                item.fill._rgbas._data,
                item.glow._size,
                item.glow._rgba._data[3] != 0.0
            )

    def init_common(self) -> None:
        self.u_fix = self.get_u_fix_in_frame(self.prog)
        self.u_glow_color = self.prog['glow_color']
        self.u_glow_size = self.prog['glow_size']

        # self.vbo_coord
        self.vbo_mapped_points = self.ctx.buffer(reserve=1)

    # endregion

    # region render

    def render_compatibility(self, item: VItem) -> None:
        if not self.initialized:
            self.init_compatibility()

        raise NotImplementedError()

    def render_normal(self, item: VItem) -> None:
        if not self.initialized:
            self.init_normal()

    # endregion

    # @staticmethod
    # def _roll_subpath(item: VItem) -> tuple[np.ndarray, np.ndarray]:
    #     points = item.points.get()

    #     look_backward = np.empty_like(points)
    #     look_forward = np.empty_like(points)

    #     start_idx = 0
    #     for end_idx in item.points.walk_subpath_end_indices():
    #         if start_idx != 0:
    #             look_backward[start_idx - 1] = NAN_POINT
    #             look_forward[start_idx - 1] = NAN_POINT

    #         subpath = points[start_idx: end_idx + 1]

    #         if np.isclose(points[end_idx], points[start_idx]).all():
    #             look_backward[start_idx: end_idx + 1] = np.roll(subpath, 1, axis=0)
    #             look_forward[start_idx: end_idx + 1] = np.roll(subpath, -1, axis=0)
    #         else:
    #             look_backward[start_idx: start_idx + 2] = NAN_POINT
    #             look_backward[start_idx + 2: end_idx + 1] = subpath[:-2]
    #             look_forward[end_idx + 1 - 2: end_idx + 1] = NAN_POINT
    #             look_forward[start_idx: end_idx + 1 - 2] = subpath[2:]

    #         start_idx = end_idx + 2

    #     print(points, look_backward, look_forward, sep='\n')

    #     return look_backward, look_forward
