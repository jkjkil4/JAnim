from __future__ import annotations

from typing import TYPE_CHECKING

import moderngl as mgl
import numpy as np

from janim.render.base import Renderer
from janim.render.framebuffer import FRAME_BUFFER_BINDING
from janim.render.program import get_janim_program
from janim.render.texture import get_texture_from_img
from janim.utils.iterables import resize_with_interpolation

if TYPE_CHECKING:
    from janim.items.image_item import ImageItem


class ImageItemRenderer(Renderer):
    def __init__(self):
        self.initialized: bool = False

    def init(self) -> None:
        self.prog = get_janim_program('render/shaders/image')

        self.u_fix = self.get_u_fix_in_frame(self.prog)
        self.u_image = self.prog['image']

        self.ctx = self.data_ctx.get().ctx
        self.vbo_points = self.ctx.buffer(reserve=4 * 3 * 4)
        self.vbo_color = self.ctx.buffer(reserve=4 * 4 * 4)
        self.vbo_texcoords = self.ctx.buffer(
            data=np.array([
                [0.0, 0.0],     # 左上
                [0.0, 1.0],     # 左下
                [1.0, 0.0],     # 右上
                [1.0, 1.0]      # 右下
            ], dtype=np.float32).tobytes()
        )

        self.vao = self.ctx.vertex_array(self.prog, [
            (self.vbo_points, '3f', 'in_point'),
            (self.vbo_color, '4f', 'in_color'),
            (self.vbo_texcoords, '2f', 'in_texcoord')
        ])

        self.prev_points = None
        self.prev_color = None
        self.prev_img = None

    def render(self, item: ImageItem) -> None:
        if not self.initialized:
            self.init()
            self.initialized = True

        new_color = item.color._rgbas.data
        new_points = item.points._points.data

        if new_color is not self.prev_color:
            color = resize_with_interpolation(new_color, 4)
            assert color.dtype == np.float32
            bytes = color.tobytes()

            assert len(bytes) == self.vbo_color.size

            self.vbo_color.write(bytes)
            self.prev_color = new_color

        if new_points is not self.prev_points:
            assert new_points.dtype == np.float32
            bytes = new_points.tobytes()

            assert len(bytes) == self.vbo_points.size

            self.vbo_points.write(bytes)
            self.prev_points = new_points

        if self.prev_img is None or item.image.img is not self.prev_img:
            self.texture = get_texture_from_img(item.image.get())
            self.texture.build_mipmaps()
            self.prev_img = item.image.img

        self.u_image.value = 0
        self.texture.filter = item.image.get_filter()
        self.texture.use(0)
        self.update_fix_in_frame(self.u_fix, item)

        # 我不知道为啥得在这里重新绑定一遍才能奏效，但是 it works ¯\_(ツ)_/¯
        if self.ctx.fbo.color_attachments is not None:
            self.prog['JA_FRAMEBUFFER'] = FRAME_BUFFER_BINDING
            self.ctx.fbo.color_attachments[0].use(FRAME_BUFFER_BINDING)

        self.vao.render(mgl.TRIANGLE_STRIP)
