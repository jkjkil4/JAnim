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


class VItemPlaneRenderer(Renderer):
    """
    对于带内部区域的 :class:`~.VItem` 所使用的渲染器
    """

    shader_path_compatibility = 'render/shaders/vitem/vitem_plane_compatibility'
    shader_path_normal = 'render/shaders/vitem/vitem_plane'

    def __init__(self):
        self.initialized: bool = False

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

        self.u_lim = self.prog['lim']

        self.sampb_mapped_points, \
            self.sampb_radius, \
            self.sampb_stroke_color, \
            self.sampb_fill_color = gl.glGenTextures(4)

        self.loc_mapped_points = gl.glGetUniformLocation(self.prog.glo, 'points')
        self.loc_radius = gl.glGetUniformLocation(self.prog.glo, 'radii')
        self.loc_stroke_color = gl.glGetUniformLocation(self.prog.glo, 'colors')
        self.loc_fill_color = gl.glGetUniformLocation(self.prog.glo, 'fills')

        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.sampb_mapped_points)
        gl.glTexBuffer(gl.GL_TEXTURE_BUFFER, gl.GL_RGBA32F, self.vbo_mapped_points.glo)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.sampb_radius)
        gl.glTexBuffer(gl.GL_TEXTURE_BUFFER, gl.GL_RGBA32F, self.vbo_radius.glo)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.sampb_stroke_color)
        gl.glTexBuffer(gl.GL_TEXTURE_BUFFER, gl.GL_RGBA32F, self.vbo_stroke_color.glo)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.sampb_fill_color)
        gl.glTexBuffer(gl.GL_TEXTURE_BUFFER, gl.GL_RGBA32F, self.vbo_fill_color.glo)

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
        def get(render_data: RenderData, item: VItem) -> VItemPlaneRenderer.RenderAttrs:
            return VItemPlaneRenderer.RenderAttrs(
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
        self.u_stroke_background: mgl.Uniform = self.prog['stroke_background']
        self.u_is_fill_transparent = self.prog['is_fill_transparent']
        self.u_glow_color = self.prog['glow_color']
        self.u_glow_size = self.prog['glow_size']

        self.u_unit_normal = self.prog['unit_normal']
        self.u_start_point = self.prog['start_point']
        self.u_DEPTH_TEST = self.prog['DEPTH_TEST']
        self.u_SHADE_IN_3D = self.prog.get('SHADE_IN_3D', None)

        self.vbo_coord = self.ctx.buffer(reserve=4 * 2 * 4)
        self.vbo_mapped_points = self.ctx.buffer(reserve=1)
        self.vbo_radius = self.ctx.buffer(reserve=1)
        self.vbo_stroke_color = self.ctx.buffer(reserve=1)
        self.vbo_fill_color = self.ctx.buffer(reserve=1)

        self.vao = self.ctx.vertex_array(self.prog, self.vbo_coord, 'in_coord')

        self.attrs = self.RenderAttrs()
        self.fill_transparent = False
        self.unit_normal: np.ndarray | None = None

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

        if self._needs_update_clip_box(new_attrs):
            self._update_clip_box(item, render_data, new_attrs)

            self.attrs.glow_size = new_attrs.glow_size
            self.attrs.glow_visible = new_attrs.glow_visible

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

        if new_attrs.fill is not self.attrs.fill:
            # 这里使用 bool 将 np.bool 进行转换，使得能正常传入 uniform
            self.fill_transparent = bool(item.fill.is_transparent())

        if new_attrs.fill is not self.attrs.fill or points_cnt_changed:
            self.update_dynamic_buffer_data(new_attrs.fill,
                                            self.vbo_fill_color,
                                            resize_target)
            self.attrs.fill = new_attrs.fill

        if item._depth_test or item._shade_in_3d:
            if new_attrs.points is not self.attrs.points:
                self.unit_normal = item.points.unit_normal

        self._update_points_compatibility(item, new_attrs)

        gl.glUseProgram(self.prog.glo)
        gl.glUniform1i(self.loc_mapped_points, 0)
        gl.glUniform1i(self.loc_radius, 1)
        gl.glUniform1i(self.loc_stroke_color, 2)
        gl.glUniform1i(self.loc_fill_color, 3)

        self.u_lim.value = (len(new_attrs.points) - 1) // 2 * 2
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.sampb_mapped_points)
        gl.glActiveTexture(gl.GL_TEXTURE1)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.sampb_radius)
        gl.glActiveTexture(gl.GL_TEXTURE2)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.sampb_stroke_color)
        gl.glActiveTexture(gl.GL_TEXTURE3)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.sampb_fill_color)

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

        if self._needs_update_clip_box(new_attrs):
            self._update_clip_box(item, render_data, new_attrs)

            self.attrs.glow_size = new_attrs.glow_size
            self.attrs.glow_visible = new_attrs.glow_visible

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

        if new_attrs.fill is not self.attrs.fill:
            # 这里使用 bool 将 np.bool 进行转换，使得能正常传入 uniform
            self.fill_transparent = bool(item.fill.is_transparent())

        if new_attrs.fill is not self.attrs.fill or points_cnt_changed:
            self.update_dynamic_buffer_data(new_attrs.fill,
                                            self.vbo_fill_color,
                                            resize_target)
            self.attrs.fill = new_attrs.fill

        if item._depth_test or item._shade_in_3d:
            if new_attrs.points is not self.attrs.points:
                self.unit_normal = item.points.unit_normal

        self._update_points_normal(item, new_attrs)

        self.vbo_mapped_points.bind_to_storage_buffer(0)
        self.vbo_radius.bind_to_storage_buffer(1)
        self.vbo_stroke_color.bind_to_storage_buffer(2)
        self.vbo_fill_color.bind_to_storage_buffer(3)

        self.render_common(item, render_data, new_attrs)

    def render_common(self, item: VItem, render_data: RenderData, new_attrs: RenderAttrs) -> None:
        self.update_fix_in_frame(self.u_fix, item)
        self.u_stroke_background.value = item.stroke_background
        self.u_is_fill_transparent.value = self.fill_transparent
        self.u_glow_color.write(item.glow._rgba._data.tobytes())
        self.u_glow_size.value = new_attrs.glow_size

        self.u_DEPTH_TEST.value = item._depth_test
        if self.u_SHADE_IN_3D is not None:
            self.u_SHADE_IN_3D.value = item._shade_in_3d

        if item._depth_test or item._shade_in_3d:
            self.u_unit_normal.value = self.unit_normal
            self.u_start_point.value = new_attrs.points[0]

        with self.depth_test_if_enabled(self.ctx, item):
            self.vao.render(mgl.TRIANGLE_STRIP)

    def _update_others(self, item: VItem, render_data: RenderData, new_attrs: RenderAttrs) -> None:
        pass

    def _needs_update_clip_box(self, new_attrs: RenderAttrs) -> bool:
        return (
            new_attrs.fix_in_frame != self.attrs.fix_in_frame
            or new_attrs.radius is not self.attrs.radius
            or new_attrs.glow_size != self.attrs.glow_size
            or new_attrs.glow_visible != self.attrs.glow_visible
            or new_attrs.points is not self.attrs.points
            or new_attrs.camera_info is not self.attrs.camera_info
        )

    def _update_clip_box(self, item: VItem, render_data: RenderData, new_attrs: RenderAttrs) -> None:
        corners = np.array(item.points.self_box.get_corners())
        if new_attrs.fix_in_frame:
            clip_box = new_attrs.camera_info.map_fixed_in_frame_points(corners)
        else:
            clip_box = new_attrs.camera_info.map_points(corners)
        clip_box *= new_attrs.camera_info.frame_radius

        buff = new_attrs.radius.max() + render_data.anti_alias_radius
        if new_attrs.glow_visible:
            buff = max(buff, new_attrs.glow_size)
        clip_min = np.min(clip_box, axis=0) - buff
        clip_max = np.max(clip_box, axis=0) + buff
        clip_box = np.array([
            clip_min,
            [clip_min[0], clip_max[1]],
            [clip_max[0], clip_min[1]],
            clip_max
        ]) / new_attrs.camera_info.frame_radius
        clip_box = np.clip(clip_box, -1, 1)

        bytes = clip_box.astype(np.float32).tobytes()
        assert len(bytes) == self.vbo_coord.size
        self.vbo_coord.write(bytes)

    def _update_points_compatibility(self, item: VItem, new_attrs: RenderAttrs) -> None:
        if new_attrs.points is not self.attrs.points \
                or new_attrs.fix_in_frame != self.attrs.fix_in_frame \
                or new_attrs.camera_info is not self.attrs.camera_info:
            if new_attrs.fix_in_frame:
                mapped = new_attrs.camera_info.map_fixed_in_frame_points(new_attrs.points)
            else:
                mapped = new_attrs.camera_info.map_points(new_attrs.points)
            mapped *= new_attrs.camera_info.frame_radius

            if len(self.points_vec4buffer) != len(mapped):
                self.points_vec4buffer = np.empty((len(mapped), 4), dtype=np.float32)

            self.points_vec4buffer[:, :2] = mapped
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
