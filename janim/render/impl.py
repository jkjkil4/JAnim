
from typing import TYPE_CHECKING

import moderngl as mgl
import numpy as np

from janim.render.base import Renderer, get_program
from janim.utils.iterables import resize_with_interpolation

if TYPE_CHECKING:
    from janim.items.points import DotCloud


class DotCloudRenderer(Renderer):
    def init(self) -> None:
        self.prog = get_program('render/shaders/dotcloud')
        self.vao = None

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
