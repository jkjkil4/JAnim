from __future__ import annotations

from typing import TYPE_CHECKING

import moderngl as mgl
import numpy as np
import OpenGL.GL as gl

from janim.render.base import Renderer
from janim.render.program import get_janim_compute_shader, get_janim_program
from janim.utils.iterables import resize_with_interpolation

if TYPE_CHECKING:
    from janim.items.vitem import VItem


class VItemRenderer(Renderer):
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

    # region compatibility

    def init_compatibility(self) -> None:
        self.prog = get_janim_program('render/shaders/vitem_compatibility')

        self.u_lim = self.prog['lim']

        self.u_fix = self.get_u_fix_in_frame(self.prog)
        self.u_stroke_background: mgl.Uniform = self.prog['stroke_background']
        self.u_is_fill_transparent = self.prog['is_fill_transparent']
        self.u_glow_color = self.prog['glow_color']
        self.u_glow_size = self.prog['glow_size']

        self.vbo_coord = self.ctx.buffer(reserve=4 * 2 * 4)
        self.vbo_mapped_points = self.ctx.buffer(reserve=1)
        self.vbo_radius = self.ctx.buffer(reserve=1)
        self.vbo_stroke_color = self.ctx.buffer(reserve=1)
        self.vbo_fill_color = self.ctx.buffer(reserve=1)

        self.vao = self.ctx.vertex_array(self.prog, self.vbo_coord, 'in_coord')

        self.prev_camera_info = None

        self.prev_fix_in_frame = None
        self.prev_points = None
        self.prev_radius = None
        self.prev_stroke = None
        self.prev_fill = None
        self.fill_transparent = False
        self.prev_glow_size = -1
        self.prev_glow_visible = -1

        self.points_vec4buffer = np.empty((0, 4), dtype=np.float32)

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

    def render_compatibility(self, item: VItem) -> None:
        if not self.initialized:
            self.init_compatibility()
            self.initialized = True

        new_points = item.points._points.data

        if len(new_points) < 3:
            return
        render_data = self.data_ctx.get()

        new_camera_info = render_data.camera_info
        new_fix_in_frame = item._fix_in_frame
        new_radius = item.radius._radii._data
        new_stroke = item.stroke._rgbas._data
        new_fill = item.fill._rgbas._data
        new_glow_size = item.glow._size
        new_glow_visible = item.glow._rgba._data[3] != 0.0

        is_camera_changed = new_camera_info is not self.prev_camera_info

        if new_fix_in_frame != self.prev_fix_in_frame \
                or new_radius is not self.prev_radius \
                or new_glow_size != self.prev_glow_size \
                or new_glow_visible != self.prev_glow_visible \
                or new_points is not self.prev_points \
                or is_camera_changed:
            corners = np.array(item.points.self_box.get_corners())
            if new_fix_in_frame:
                clip_box = new_camera_info.map_fixed_in_frame_points(corners)
            else:
                clip_box = new_camera_info.map_points(corners)
            clip_box *= new_camera_info.frame_radius

            buff = new_radius.max() + render_data.anti_alias_radius
            if new_glow_visible:
                buff = max(buff, new_glow_size)
            clip_min = np.min(clip_box, axis=0) - buff
            clip_max = np.max(clip_box, axis=0) + buff
            clip_box = np.array([
                clip_min,
                [clip_min[0], clip_max[1]],
                [clip_max[0], clip_min[1]],
                clip_max
            ]) / new_camera_info.frame_radius
            clip_box = np.clip(clip_box, -1, 1)

            bytes = clip_box.astype(np.float32).tobytes()
            assert len(bytes) == self.vbo_coord.size
            self.vbo_coord.write(bytes)

            self.prev_glow_size = new_glow_size
            self.prev_glow_visible = new_glow_visible

        if new_radius is not self.prev_radius or len(new_points) != len(self.prev_points):
            radius = resize_with_interpolation(new_radius, (len(new_points) + 1) // 2)
            assert radius.dtype == np.float32
            bytes = radius.tobytes()

            size = (len(bytes) + 31) & ~31  # 保证一定是 32 的倍数
            if len(bytes) != self.vbo_radius.size:
                self.vbo_radius.orphan(size)

            self.vbo_radius.write(bytes)
            self.prev_radius = new_radius

        if new_stroke is not self.prev_stroke or len(new_points) != len(self.prev_points):
            stroke = resize_with_interpolation(new_stroke, (len(new_points) + 1) // 2)
            assert stroke.dtype == np.float32
            bytes = stroke.tobytes()

            if len(bytes) != self.vbo_stroke_color.size:
                self.vbo_stroke_color.orphan(len(bytes))

            self.vbo_stroke_color.write(bytes)
            self.prev_stroke = new_stroke

        if new_fill is not self.prev_fill:
            # 这里使用 bool 将 np.bool 进行转换，使得能正常传入 uniform
            self.fill_transparent = bool(item.fill.is_transparent())

        if new_fill is not self.prev_fill or len(new_points) != len(self.prev_points):
            fill = resize_with_interpolation(new_fill, (len(new_points) + 1) // 2)
            assert fill.dtype == np.float32
            bytes = fill.tobytes()

            if len(bytes) != self.vbo_fill_color.size:
                self.vbo_fill_color.orphan(len(bytes))

            self.vbo_fill_color.write(bytes)
            self.prev_fill = new_fill

        if new_points is not self.prev_points \
                or new_fix_in_frame != self.prev_fix_in_frame \
                or is_camera_changed:
            if new_fix_in_frame:
                mapped = new_camera_info.map_fixed_in_frame_points(new_points)
            else:
                mapped = new_camera_info.map_points(new_points)
            mapped *= new_camera_info.frame_radius

            if len(self.points_vec4buffer) != len(mapped):
                self.points_vec4buffer = np.empty((len(mapped), 4), dtype=np.float32)

            self.points_vec4buffer[:, :2] = mapped
            self.points_vec4buffer[:, 2] = item.points.get_closepath_flags().astype(np.float32)
            bytes = self.points_vec4buffer.tobytes()

            if len(bytes) != self.vbo_mapped_points.size:
                self.vbo_mapped_points.orphan(len(bytes))

            self.vbo_mapped_points.write(bytes)
            self.prev_fix_in_frame = new_fix_in_frame
            self.prev_camera_info = new_camera_info
            self.prev_points = new_points

        gl.glUseProgram(self.prog.glo)
        gl.glUniform1i(self.loc_mapped_points, 0)
        gl.glUniform1i(self.loc_radius, 1)
        gl.glUniform1i(self.loc_stroke_color, 2)
        gl.glUniform1i(self.loc_fill_color, 3)

        self.u_lim.value = (len(new_points) - 1) // 2 * 2
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.sampb_mapped_points)
        gl.glActiveTexture(gl.GL_TEXTURE1)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.sampb_radius)
        gl.glActiveTexture(gl.GL_TEXTURE2)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.sampb_stroke_color)
        gl.glActiveTexture(gl.GL_TEXTURE3)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, self.sampb_fill_color)

        self.update_fix_in_frame(self.u_fix, item)
        self.u_stroke_background.value = item.stroke_background
        self.u_is_fill_transparent.value = self.fill_transparent
        self.u_glow_color.write(item.glow._rgba._data.tobytes())
        self.u_glow_size.value = new_glow_size

        self.vao.render(mgl.TRIANGLE_STRIP)

    # endregion

    # region normal

    def init_normal(self) -> None:
        self.comp = get_janim_compute_shader('render/shaders/map_points.comp.glsl')

        self.comp_u_fix = self.get_u_fix_in_frame(self.comp)

        self.prog = get_janim_program('render/shaders/vitem')

        self.u_fix = self.get_u_fix_in_frame(self.prog)
        self.u_stroke_background: mgl.Uniform = self.prog['stroke_background']
        self.u_is_fill_transparent = self.prog['is_fill_transparent']
        self.u_glow_color = self.prog['glow_color']
        self.u_glow_size = self.prog['glow_size']

        self.vbo_coord = self.ctx.buffer(reserve=4 * 2 * 4)
        self.vbo_points = self.ctx.buffer(reserve=1)
        self.vbo_mapped_points = self.ctx.buffer(reserve=1)
        self.vbo_radius = self.ctx.buffer(reserve=1)
        self.vbo_stroke_color = self.ctx.buffer(reserve=1)
        self.vbo_fill_color = self.ctx.buffer(reserve=1)

        self.vao = self.ctx.vertex_array(self.prog, self.vbo_coord, 'in_coord')

        self.prev_camera_info = None

        self.prev_fix_in_frame = None
        self.prev_points = None
        self.prev_radius = None
        self.prev_stroke = None
        self.prev_fill = None
        self.fill_transparent = False
        self.prev_glow_size = -1
        self.prev_glow_visible = -1

        self.points_vec4buffer = np.empty((0, 4), dtype=np.float32)

    def render_normal(self, item: VItem) -> None:
        if not self.initialized:
            self.init_normal()
            self.initialized = True

        new_points = item.points._points.data

        if len(new_points) < 3:
            return
        render_data = self.data_ctx.get()

        new_camera_info = render_data.camera_info
        new_fix_in_frame = item._fix_in_frame
        new_radius = item.radius._radii._data
        new_stroke = item.stroke._rgbas._data
        new_fill = item.fill._rgbas._data
        new_glow_size = item.glow._size
        new_glow_visible = item.glow._rgba._data[3] != 0.0

        is_camera_changed = new_camera_info is not self.prev_camera_info

        if new_fix_in_frame != self.prev_fix_in_frame \
                or new_radius is not self.prev_radius \
                or new_glow_size != self.prev_glow_size \
                or new_glow_visible != self.prev_glow_visible \
                or new_points is not self.prev_points \
                or is_camera_changed:
            corners = np.array(item.points.self_box.get_corners())
            if new_fix_in_frame:
                clip_box = new_camera_info.map_fixed_in_frame_points(corners)
            else:
                clip_box = new_camera_info.map_points(corners)
            clip_box *= new_camera_info.frame_radius

            buff = new_radius.max() + render_data.anti_alias_radius
            if new_glow_visible:
                buff = max(buff, new_glow_size)
            clip_min = np.min(clip_box, axis=0) - buff
            clip_max = np.max(clip_box, axis=0) + buff
            clip_box = np.array([
                clip_min,
                [clip_min[0], clip_max[1]],
                [clip_max[0], clip_min[1]],
                clip_max
            ]) / new_camera_info.frame_radius
            clip_box = np.clip(clip_box, -1, 1)

            bytes = clip_box.astype(np.float32).tobytes()
            assert len(bytes) == self.vbo_coord.size
            self.vbo_coord.write(bytes)

            self.prev_glow_size = new_glow_size
            self.prev_glow_visible = new_glow_visible

        if new_radius is not self.prev_radius or len(new_points) != len(self.prev_points):
            radius = resize_with_interpolation(new_radius, (len(new_points) + 1) // 2)
            assert radius.dtype == np.float32
            bytes = radius.tobytes()

            if len(bytes) != self.vbo_radius.size:
                self.vbo_radius.orphan(len(bytes))

            self.vbo_radius.write(bytes)
            self.prev_radius = new_radius

        if new_stroke is not self.prev_stroke or len(new_points) != len(self.prev_points):
            stroke = resize_with_interpolation(new_stroke, (len(new_points) + 1) // 2)
            assert stroke.dtype == np.float32
            bytes = stroke.tobytes()

            if len(bytes) != self.vbo_stroke_color.size:
                self.vbo_stroke_color.orphan(len(bytes))

            self.vbo_stroke_color.write(bytes)
            self.prev_stroke = new_stroke

        if new_fill is not self.prev_fill:
            # 这里使用 bool 将 np.bool 进行转换，使得能正常传入 uniform
            self.fill_transparent = bool(item.fill.is_transparent())

        if new_fill is not self.prev_fill or len(new_points) != len(self.prev_points):
            fill = resize_with_interpolation(new_fill, (len(new_points) + 1) // 2)
            assert fill.dtype == np.float32
            bytes = fill.tobytes()

            if len(bytes) != self.vbo_fill_color.size:
                self.vbo_fill_color.orphan(len(bytes))

            self.vbo_fill_color.write(bytes)
            self.prev_fill = new_fill

        if new_points is not self.prev_points:
            if len(self.points_vec4buffer) != len(new_points):
                self.points_vec4buffer = np.empty((len(new_points), 4), dtype=np.float32)

            self.points_vec4buffer[:, :3] = new_points
            self.points_vec4buffer[:, 3] = item.points.get_closepath_flags().astype(np.float32)
            bytes = self.points_vec4buffer.tobytes()

            if len(bytes) != self.vbo_points.size:
                self.vbo_points.orphan(len(bytes))

            self.vbo_points.write(bytes)

        if new_points is not self.prev_points \
                or new_fix_in_frame != self.prev_fix_in_frame \
                or is_camera_changed:
            if self.vbo_points.size != self.vbo_mapped_points.size:
                self.vbo_mapped_points.orphan(self.vbo_points.size)

            self.vbo_points.bind_to_storage_buffer(0)
            self.vbo_mapped_points.bind_to_storage_buffer(1)
            self.update_fix_in_frame(self.comp_u_fix, item)
            self.comp.run(group_x=(len(new_points) + 255) // 256)   # 相当于 len() / 256 向上取整

            self.prev_fix_in_frame = new_fix_in_frame
            self.prev_camera_info = new_camera_info
            self.prev_points = new_points

        self.vbo_mapped_points.bind_to_storage_buffer(0)
        self.vbo_radius.bind_to_storage_buffer(1)
        self.vbo_stroke_color.bind_to_storage_buffer(2)
        self.vbo_fill_color.bind_to_storage_buffer(3)

        self.update_fix_in_frame(self.u_fix, item)
        self.u_stroke_background.value = item.stroke_background
        self.u_is_fill_transparent.value = self.fill_transparent
        self.u_glow_color.write(item.glow._rgba._data.tobytes())
        self.u_glow_size.value = new_glow_size

        self.vao.render(mgl.TRIANGLE_STRIP)

    # endregion
