from __future__ import annotations

from typing import TYPE_CHECKING

import moderngl as mgl
import numpy as np

from janim.render.base import Renderer
from janim.render.program import get_program_from_file_prefix
from janim.utils.space_ops import normalize_along_axis

if TYPE_CHECKING:
    from janim.items.three_d.types import CheckerboardSurface


class CheckerboardSurfaceRenderer(Renderer):
    def __init__(self):
        self.initialized: bool = False

    def init(self) -> None:
        self.prog = get_program_from_file_prefix('render/shaders/checkerboard_surface')

        self.u_fix = self.get_u_fix_in_frame(self.prog)
        self.u_color1 = self.prog['u_color1']
        self.u_color2 = self.prog['u_color2']
        self.u_row_length = self.prog['u_row_length']

        self.ctx = self.data_ctx.get().ctx
        self.vbo_points = self.ctx.buffer(reserve=1)
        self.vbo_normals = self.ctx.buffer(reserve=1)
        self.ibo = self.ctx.buffer(reserve=1)

        self.vao = self.ctx.vertex_array(
            self.prog,
            [
                (self.vbo_points, '3f', 'in_point'),
                (self.vbo_normals, '3f', 'in_normal'),
            ],
            index_buffer=self.ibo,
        )

        self.prev_points = None
        self.prev_dupoints = None
        self.prev_dvpoints = None
        self.prev_indices = None

    def render(self, item: CheckerboardSurface) -> None:
        if not self.initialized:
            self.init()
            self.initialized = True

        new_points = item.points._points.data
        new_dupoints = item._du_points._points.data
        new_dvpoints = item._dv_points._points.data
        new_indices = item._tri_indices

        if (
            new_points is not self.prev_points
            or new_dupoints is not self.prev_dupoints
            or new_dvpoints is not self.prev_dvpoints
        ):
            crosses = np.cross(new_dupoints - new_points, new_dvpoints - new_points)
            self.normals = normalize_along_axis(crosses, 1)
            self.update_dynamic_buffer_data(self.normals, self.vbo_normals, len(self.normals))

            self.prev_dupoints = new_dupoints
            self.prev_dvpoints = new_dvpoints

        if new_points is not self.prev_points:
            self.update_dynamic_buffer_data(new_points, self.vbo_points, len(new_points))
            self.prev_points = new_points

        if new_indices is not self.prev_indices:
            self.update_dynamic_buffer_data(
                new_indices, self.ibo, len(new_indices), assert_dtype='i4'
            )
            self.prev_indices = new_indices

        self.update_fix_in_frame(self.u_fix, item)
        self.u_color1.value = item.color._rgbas._data[0]
        self.u_color2.value = item.color._rgbas._data[1]
        self.u_row_length.value = item.resolution[1]

        with self.depth_test_if_enabled(self.ctx, item):
            self.vao.render(mgl.TRIANGLES, vertices=new_indices.size)
