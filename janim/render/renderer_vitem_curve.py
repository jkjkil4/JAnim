from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import moderngl as mgl
import numpy as np
import OpenGL.GL as gl

from janim.camera.camera_info import CameraInfo
from janim.render.base import RenderData, Renderer
from janim.render.program import (get_compute_shader_from_file,
                                  get_program_from_file_prefix)

if TYPE_CHECKING:
    from janim.items.vitem import VItem


class VItemCurveRenderer(Renderer):
    """
    对于纯曲线边界 :class:`~.VItem` 所使用的渲染器
    """

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

        self.sampb_mapped_points, \
            self.sampb_radius, \
            self.sampb_stroke_color = gl.glGenTextures(3)

        self.loc_mapped_points = gl.glGetUniformLocation(self.prog.glo, 'points')
        self.loc_radius = gl.glGetUniformLocation(self.prog.glo, 'radii')
        self.loc_stroke_color = gl.glGetUniformLocation(self.prog.glo, 'colors')

        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.sampb_mapped_points)
        gl.glTexBuffer(gl.GL_TEXTURE_BUFFER, gl.GL_RGBA32F, self.vbo_mapped_points.glo)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.sampb_radius)
        gl.glTexBuffer(gl.GL_TEXTURE_BUFFER, gl.GL_RGBA32F, self.vbo_radius.glo)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.sampb_stroke_color)
        gl.glTexBuffer(gl.GL_TEXTURE_BUFFER, gl.GL_RGBA32F, self.vbo_stroke_color.glo)

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

        self.vao = self.ctx.vertex_array(self.prog, self.vbo_indices, 'in_indices')

        self.attrs = self.RenderAttrs()

        self.points_vec4buffer = np.empty((0, 4), dtype=np.float32)

    # endregion

    # region render

    def render_compatibility(self, item: VItem) -> None:
        if not self.initialized:
            self.init_compatibility()
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
                                            resize_target,
                                            use_32bit_align=True)
            self.attrs.radius = new_attrs.radius

        if new_attrs.stroke is not self.attrs.stroke or points_cnt_changed:
            self.update_dynamic_buffer_data(new_attrs.stroke,
                                            self.vbo_stroke_color,
                                            resize_target)
            self.attrs.stroke = new_attrs.stroke

        if new_attrs.points is not self.attrs.points:
            self._update_indices(item, new_attrs)

        self._update_points_compatibility(item, new_attrs)

        gl.glUseProgram(self.prog.glo)
        gl.glUniform1i(self.loc_mapped_points, 0)
        gl.glUniform1i(self.loc_radius, 1)
        gl.glUniform1i(self.loc_stroke_color, 2)

        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.sampb_mapped_points)
        gl.glActiveTexture(gl.GL_TEXTURE1)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.sampb_radius)
        gl.glActiveTexture(gl.GL_TEXTURE2)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.sampb_stroke_color)

        self.render_common(item, render_data, new_attrs)

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
            self.attrs.stroke = new_attrs.stroke

        if new_attrs.points is not self.attrs.points:
            self._update_indices(item, new_attrs)

        self._update_points_normal(item, new_attrs)

        self.vbo_mapped_points.bind_to_storage_buffer(0)
        self.vbo_radius.bind_to_storage_buffer(1)
        self.vbo_stroke_color.bind_to_storage_buffer(2)

        self.render_common(item, render_data, new_attrs)

    def render_common(self, item: VItem, render_data: RenderData, new_attrs: RenderAttrs) -> None:
        self.update_fix_in_frame(self.u_fix, item)
        self.u_glow_color.write(item.glow._rgba._data.tobytes())
        self.u_glow_size.value = item.glow._size

        with self.depth_test_if_enabled(self.ctx, item):
            self.vao.render(mgl.POINTS, vertices=self.vbo_indices.size // 4 // 3)

    def _update_others(self, item: VItem, render_data: RenderData, new_attrs: RenderAttrs) -> None:
        pass

    def _update_indices(self, item: VItem, new_attrs: RenderAttrs) -> None:
        points = new_attrs.points
        indices_list = []

        start_idx = 0
        for end_idx in item.points.walk_subpath_end_indices():
            is_closed = np.isclose(points[end_idx], points[start_idx]).all()

            curr_indices = np.arange(start_idx, end_idx, 2, dtype=np.int32)
            mask = np.isclose(points[curr_indices], points[curr_indices + 2])
            mask = np.all(mask, axis=1)
            curr_indices = curr_indices[~mask]

            prev_indices = np.empty_like(curr_indices)
            if len(prev_indices) != 0:
                prev_indices[1:] = curr_indices[:-1]
                prev_indices[0] = curr_indices[-1] if is_closed else -1

            next_indices = np.empty_like(curr_indices)
            if len(next_indices) != 0:
                next_indices[:-1] = curr_indices[1:]
                next_indices[-1] = curr_indices[0] if is_closed else -1

            indices_list.append(
                np.vstack([prev_indices, curr_indices, next_indices]).T
            )

        all_indices = indices_list[0] if len(indices_list) == 1 else np.vstack(indices_list)
        bytes = all_indices.tobytes()

        if len(bytes) != self.vbo_indices.size:
            self.vbo_indices.orphan(len(bytes))

        self.vbo_indices.write(bytes)

    def _update_points_compatibility(self, item: VItem, new_attrs: RenderAttrs) -> None:
        if new_attrs.points is not self.attrs.points \
                or new_attrs.fix_in_frame != self.attrs.fix_in_frame \
                or new_attrs.camera_info is not self.attrs.camera_info:
            if new_attrs.fix_in_frame:
                mapped = new_attrs.camera_info.map_fixed_in_frame_points_with_depth(new_attrs.points)
            else:
                mapped = new_attrs.camera_info.map_points_with_depth(new_attrs.points)
            mapped[:, :2] *= new_attrs.camera_info.frame_radius

            if len(self.points_vec4buffer) != len(mapped):
                self.points_vec4buffer = np.empty((len(mapped), 4), dtype=np.float32)

            self.points_vec4buffer[:, :3] = mapped
            bytes = self.points_vec4buffer.tobytes()

            if len(bytes) != self.vbo_mapped_points.size:
                self.vbo_mapped_points.orphan(len(bytes))

            self.vbo_mapped_points.write(bytes)
            self.attrs.fix_in_frame = new_attrs.fix_in_frame
            self.attrs.camera_info = new_attrs.camera_info
            self.attrs.points = new_attrs.points

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
