
from typing import TYPE_CHECKING

import moderngl as mgl
import numpy as np

from janim.render.base import Renderer, get_program
from janim.utils.iterables import resize_with_interpolation

if TYPE_CHECKING:
    from janim.items.points import DotCloud
    from janim.items.vitem import VItem


class DotCloudRenderer(Renderer):
    def init(self) -> None:
        self.prog = get_program('render/shaders/dotcloud')

        self.ctx = self.data_ctx.get().ctx
        self.vbo_points = self.ctx.buffer(reserve=1)
        self.vbo_color = self.ctx.buffer(reserve=1)
        self.vbo_radius = self.ctx.buffer(reserve=1)

        self.vao = self.ctx.vertex_array(self.prog, [
            (self.vbo_points, '3f', 'in_point'),
            (self.vbo_color, '4f', 'in_color'),
            (self.vbo_radius, '1f', 'in_radius')
        ])

        self.prev_points = np.array([])
        self.prev_color = np.array([])
        self.prev_radius = np.array([])

    def render(self, data: 'DotCloud.Data') -> None:
        new_color = data.cmpt.color.get()
        new_radius = data.cmpt.radius.get()
        new_points = data.cmpt.points.get()

        if id(new_color) != id(self.prev_color) or len(new_points) != len(self.prev_points):
            color = resize_with_interpolation(new_color, len(new_points))
            bytes = color.astype('f4').tobytes()

            if len(bytes) != self.vbo_color.size:
                self.vbo_color.orphan(len(bytes))

            self.vbo_color.write(bytes)
            self.prev_color = new_color

        if id(new_radius) != id(self.prev_radius) or len(new_points) != len(self.prev_points):
            radius = resize_with_interpolation(new_radius, len(new_points))
            bytes = radius.astype('f4').tobytes()

            if len(bytes) != self.vbo_radius.size:
                self.vbo_radius.orphan(len(bytes))

            self.vbo_radius.write(bytes)
            self.prev_radius = new_radius

        if id(new_points) != id(self.prev_points):
            bytes = new_points.astype('f4').tobytes()

            if len(bytes) != self.vbo_points.size:
                self.vbo_points.orphan(len(bytes))

            self.vbo_points.write(bytes)
            self.prev_points = new_points

        self.vao.render(mgl.POINTS, vertices=len(self.prev_points))


class VItemRenderer(Renderer):
    def init(self) -> None:
        self.prog = get_program('render/shaders/vitem')

        self.ctx = self.data_ctx.get().ctx
        self.vbo_coord = self.ctx.buffer(
            np.array([
                -1.0, -1.0,
                -1.0, 1.0,
                1.0, -1.0,
                1.0, 1.0,
            ], dtype='f4').tobytes()
        )
        self.vbo_mapped_points = self.ctx.buffer(reserve=1)
        self.vbo_radius = self.ctx.buffer(reserve=1)
        self.vbo_stroke_color = self.ctx.buffer(reserve=1)
        self.vbo_fill_color = self.ctx.buffer(reserve=1)

        self.vao = self.ctx.vertex_array(self.prog, self.vbo_coord, 'in_coord')

        self.prev_camera_info = None

        self.prev_points = np.array([])
        self.prev_radius = np.array([])
        self.prev_stroke = np.array([])
        self.prev_fill = np.array([])

    def render(self, data: 'VItem.Data[VItem]') -> None:
        render_data = self.data_ctx.get()

        new_camera_info = render_data.camera_info

        new_points = data.cmpt.points.get()
        new_radius = data.cmpt.radius.get()
        new_stroke = data.cmpt.stroke.get()
        new_fill = data.cmpt.fill.get()

        if id(new_radius) != id(self.prev_radius) or len(new_points) != len(self.prev_points):
            radius = resize_with_interpolation(new_radius, (len(new_points) + 1) // 2)
            bytes = radius.astype('f4').tobytes()

            if len(bytes) != self.vbo_radius.size:
                self.vbo_radius.orphan(len(bytes))

            self.vbo_radius.write(bytes)
            self.prev_radius = new_radius

        if id(new_stroke) != id(self.prev_stroke) or len(new_points) != len(self.prev_points):
            stroke = resize_with_interpolation(new_stroke, (len(new_points) + 1) // 2)
            bytes = stroke.astype('f4').tobytes()

            if len(bytes) != self.vbo_stroke_color.size:
                self.vbo_stroke_color.orphan(len(bytes))

            self.vbo_stroke_color.write(bytes)
            self.prev_stroke = new_stroke

        if id(new_fill) != id(self.prev_fill) or len(new_points) != len(self.prev_points):
            fill = resize_with_interpolation(new_fill, (len(new_points) + 1) // 2)
            bytes = fill.astype('f4').tobytes()

            if len(bytes) != self.vbo_fill_color.size:
                self.vbo_fill_color.orphan(len(bytes))

            self.vbo_fill_color.write(bytes)
            self.prev_fill = new_fill

        if id(new_points) != id(self.prev_points) or id(new_camera_info) != id(self.prev_camera_info):
            mapped = np.hstack([
                new_points,
                np.full((len(new_points), 1), 1)
            ])
            mapped = np.dot(mapped, render_data.camera_info.view_matrix.T)
            mapped = np.dot(mapped, render_data.camera_info.proj_matrix.T)
            mapped /= np.repeat(mapped[:, 3], 4).reshape((len(mapped), 4))
            mapped[:, :2] *= render_data.camera_info.frame_radius

            bytes = np.hstack([
                mapped[:, :2],
                data.cmpt.points.get_closepath_flags().reshape((len(mapped), 1)),
                np.zeros((len(mapped), 1))
            ]).astype('f4').tobytes()

            if len(bytes) != self.vbo_mapped_points.size:
                self.vbo_mapped_points.orphan(len(bytes))

            self.vbo_mapped_points.write(bytes)
            self.prev_camera_info = new_camera_info
            self.prev_points = new_points

        self.vbo_mapped_points.bind_to_storage_buffer(0)
        self.vbo_radius.bind_to_storage_buffer(1)
        self.vbo_stroke_color.bind_to_storage_buffer(2)
        self.vbo_fill_color.bind_to_storage_buffer(3)
        self.vao.render(mgl.TRIANGLE_STRIP)
