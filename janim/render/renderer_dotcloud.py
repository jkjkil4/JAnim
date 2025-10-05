from __future__ import annotations

from typing import TYPE_CHECKING

import moderngl as mgl
import numpy as np

from janim.render.base import Renderer
from janim.render.program import get_program_from_file_prefix

if TYPE_CHECKING:
    from janim.items.points import DotCloud


class DotCloudRenderer(Renderer):
    def __init__(self):
        self.initialized = False

    def init(self) -> None:
        self.prog = get_program_from_file_prefix('render/shaders/dotcloud')

        self.u_fix = self.get_u_fix_in_frame(self.prog)
        self.u_glow_color = self.prog['glow_color']
        self.u_glow_size = self.prog['glow_size']

        self.ctx = self.data_ctx.get().ctx
        self.vbo_points = self.ctx.buffer(reserve=1)
        self.vbo_color = self.ctx.buffer(reserve=1)
        self.vbo_radius = self.ctx.buffer(reserve=1)

        self.vao = self.ctx.vertex_array(self.prog, [
            (self.vbo_points, '3f', 'in_point'),
            (self.vbo_color, '4f', 'in_color'),
            (self.vbo_radius, '1f', 'in_radius')
        ])

        self.prev_points = None
        self.prev_color = None
        self.prev_radius = None

    def render(self, item: DotCloud) -> None:
        if not self.initialized:
            self.init()
            self.initialized = True

        new_color = item.color._rgbas.data
        new_radius = item.radius._radii.data
        new_points = item.points._points.data

        if new_color is not self.prev_color or len(new_points) != len(self.prev_points):
            self.update_dynamic_buffer_data(new_color, self.vbo_color, len(new_points))
            self.prev_color = new_color

        if new_radius is not self.prev_radius or len(new_points) != len(self.prev_points):
            self.update_dynamic_buffer_data(new_radius, self.vbo_radius, len(new_points))
            self.prev_radius = new_radius

        if new_points is not self.prev_points:
            assert new_points.dtype == np.float32
            bytes = new_points.tobytes()

            if len(bytes) != self.vbo_points.size:
                self.vbo_points.orphan(len(bytes))

            self.vbo_points.write(bytes)
            self.prev_points = new_points

        self.update_fix_in_frame(self.u_fix, item)
        self.u_glow_color.write(item.glow._rgba._data.tobytes())
        self.u_glow_size.value = item.glow._size

        with self.depth_test_if_enabled(self.ctx, item):
            self.vao.render(mgl.POINTS, vertices=len(self.prev_points))
