
from typing import TYPE_CHECKING

import numpy as np
import moderngl as mgl

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
        self.vao = self.ctx.vertex_array(self.prog, [
            (self.vbo_points, '3f', 'in_point'),
            (self.vbo_color, '4f', 'in_color')
        ])

        self.prev_points = np.array([])
        self.prev_color = np.array([])

    def render(self, data: 'DotCloud.Data') -> None:
        new_color = data.cmpt.color.get()
        new_points = data.cmpt.points.get()

        if id(new_color) != id(self.prev_color) or len(new_points) != len(self.prev_points):
            color = resize_with_interpolation(new_color, len(new_points))
            bytes = color.astype('f4').tobytes()

            if len(bytes) != self.vbo_color.size:
                self.vbo_color.orphan(len(bytes))

            self.vbo_color.write(bytes)
            self.prev_color = new_color

        if id(new_points) != id(self.prev_points):
            bytes = new_points.astype('f4').tobytes()

            if len(bytes) != self.vbo_points.size:
                self.vbo_points.orphan(len(bytes))

            self.vbo_points.write(bytes)
            self.prev_points = new_points

        self.vao.render(mgl.TRIANGLES, vertices=len(self.prev_points))
