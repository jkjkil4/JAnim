from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import moderngl as mgl
import numpy as np

from janim.camera.camera_info import CameraInfo
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

        self.comp = get_compute_shader_from_file('render/shaders/map_points_with_depth.comp.glsl')
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

        @staticmethod
        def get(render_data: RenderData, item: VItem) -> VItemCurveRenderer.RenderAttrs:
            return VItemCurveRenderer.RenderAttrs(
                render_data.camera_info,
                item._fix_in_frame,
                item.points._points._data,
                item.radius._radii._data,
                item.stroke._rgbas._data,
                item.fill._rgbas._data
            )

    def init_common(self) -> None:
        self.u_fix = self.get_u_fix_in_frame(self.prog)
        self.u_glow_color = self.prog['glow_color']
        self.u_glow_size = self.prog['glow_size']

        self.vbo_indices = self.ctx.buffer(reserve=1)

        self.vbo_mapped_points = self.ctx.buffer(reserve=1)
        self.vbo_radius = self.ctx.buffer(reserve=1)
        self.vbo_stroke_color = self.ctx.buffer(reserve=1)
        self.vbo_fill_color = self.ctx.buffer(reserve=1)

        self.vao = self.ctx.vertex_array(self.prog, self.vbo_indices, 'in_indices')

        self.attrs = self.RenderAttrs()

        self.points_vec4buffer = np.empty((0, 4), dtype=np.float32)

    # endregion

    # region render

    def render_compatibility(self, item: VItem) -> None:
        if not self.initialized:
            self.init_compatibility()
            self.initialized = True

        raise NotImplementedError()

    def render_normal(self, item: VItem) -> None:
        if not self.initialized:
            self.init_normal()
            self.initialized = True

        render_data = self.data_ctx.get()
        new_attrs = self.RenderAttrs.get(render_data, item)
        points_cnt_changed = self.attrs.points is None or len(new_attrs.points) != len(self.attrs.points)
        resize_target = (len(new_attrs.points) + 1) // 2

        if len(new_attrs.points) < 3:
            return

        self._update_others(item, render_data, new_attrs)

        if new_attrs.radius is not self.attrs.radius or points_cnt_changed:
            self.update_dynamic_buffer_data(new_attrs.radius,
                                            self.vbo_radius,
                                            resize_target)
            self.attrs.radius = new_attrs.radius

        if new_attrs.stroke is not self.attrs.stroke or points_cnt_changed:
            self.update_dynamic_buffer_data(new_attrs.stroke,
                                            self.vbo_stroke_color,
                                            resize_target)

        if new_attrs.fill is not self.attrs.fill or points_cnt_changed:
            self.update_dynamic_buffer_data(new_attrs.fill,
                                            self.vbo_fill_color,
                                            resize_target)
            self.attrs.fill = new_attrs.fill

        if new_attrs.points is not self.attrs.points:
            self._update_indices(item, new_attrs)

        self._update_points_normal(item, new_attrs)

        self.vbo_mapped_points.bind_to_storage_buffer(0)
        self.vbo_radius.bind_to_storage_buffer(1)
        self.vbo_stroke_color.bind_to_storage_buffer(2)
        self.vbo_fill_color.bind_to_storage_buffer(3)

        self.update_fix_in_frame(self.u_fix, item)
        self.u_glow_color.write(item.glow._rgba._data.tobytes())
        self.u_glow_size.value = item.glow._size

        self.vao.render(mgl.POINTS, vertices=self.vbo_indices.size // 4 // 3)

    def _update_others(self, item: VItem, render_data: RenderData, new_attrs: RenderAttrs) -> None:
        pass

    def _update_indices(self, item: VItem, new_attrs: RenderAttrs) -> None:
        points = new_attrs.points
        indices_list = []

        start_idx = 0
        for end_idx in item.points.walk_subpath_end_indices():
            indices = np.empty(((end_idx - start_idx) // 2, 3), dtype=np.int32)
            indices[:, 0] = np.arange(start_idx, end_idx, 2, dtype=np.int32)
            if np.isclose(points[end_idx], points[start_idx]).all():
                indices[:, 1] = np.roll(indices[:, 0], 1)
                indices[:, 2] = np.roll(indices[:, 0], -1)
            else:
                indices[0, 1] = -1
                indices[1:, 1] = indices[1:, 0]
                indices[-1, 2] = -1
                indices[:-1, 2] = indices[:-1, 0]

            indices_list.append(indices)

        all_indices = indices_list[0] if len(indices_list) == 1 else np.vstack(indices_list)
        bytes = all_indices.tobytes()

        if len(bytes) != self.vbo_indices.size:
            self.vbo_indices.orphan(len(bytes))

        self.vbo_indices.write(bytes)

    def _update_points_compatibility(self, item: VItem, new_attrs: RenderAttrs) -> None:
        raise NotImplementedError()

    def _update_points_normal(self, item: VItem, new_attrs: RenderAttrs) -> None:
        if new_attrs.points is not self.attrs.points:
            if len(self.points_vec4buffer) != len(new_attrs.points):
                self.points_vec4buffer = np.empty((len(new_attrs.points), 4), dtype=np.float32)

            self.points_vec4buffer[:, :3] = new_attrs.points
            bytes = self.points_vec4buffer.tobytes()

            if len(bytes) != self.vbo_points.size:
                self.vbo_points.orphan(len(bytes))

            self.vbo_points.write(bytes)

        if new_attrs.points is not self.attrs.points \
                or new_attrs.fix_in_frame != self.attrs.fix_in_frame \
                or new_attrs.camera_info is not self.attrs.camera_info:
            if self.vbo_points.size != self.vbo_mapped_points.size:
                self.vbo_mapped_points.orphan(self.vbo_points.size)

            self.vbo_points.bind_to_storage_buffer(0)
            self.vbo_mapped_points.bind_to_storage_buffer(1)
            self.update_fix_in_frame(self.comp_u_fix, item)
            self.comp.run(group_x=(len(new_attrs.points) + 255) // 256)     # 相当于 len() / 256 向上取整

            self.attrs.fix_in_frame = new_attrs.fix_in_frame
            self.attrs.camera_info = new_attrs.camera_info
            self.attrs.points = new_attrs.points

    # endregion
