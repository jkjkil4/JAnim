from __future__ import annotations

from typing import TYPE_CHECKING

import moderngl as mgl
import numpy as np
import OpenGL.GL as gl

from janim.items.vitem import VItem
from janim.render.base import Renderer
from janim.render.framebuffer import blend_context, create_framebuffer, framebuffer_context
from janim.render.program import get_program_from_file_prefix
from janim.utils.config import Config

if TYPE_CHECKING:
    from janim.items.effect.mask import ShapeMask


class ShapeMaskRenderer(Renderer):
    """
    蒙版渲染器

    - ``fbo_content``: 渲染被遮罩物件的内容
    - ``fbo_mask``: 渲染蒙版形状（白色填充）

    通过 ``shapemask_compose`` 着色器将两者合成输出
    """

    def __init__(self):
        self.initialized: bool = False

    def init(self) -> None:
        self.ctx = Renderer.data_ctx.get().ctx
        pw, ph = Config.get.pixel_width, Config.get.pixel_height

        # 双 FBO
        self.fbo_content = create_framebuffer(self.ctx, pw, ph)
        self.fbo_mask = create_framebuffer(self.ctx, pw, ph)

        # 合成着色器
        self.prog = get_program_from_file_prefix('render/shaders/shapemask_compose')

        self.u_content_tex = self.prog['content_tex']
        self.u_mask_tex = self.prog['mask_tex']

        # 全屏四边形 VBO（in_pos + in_texcoord 交错）
        self.vbo = self.ctx.buffer(
            data=np.array(
                [
                    # in_pos        in_texcoord
                    [-1.0, -1.0, 0.0, 0.0],  # 左下
                    [-1.0, 1.0, 0.0, 1.0],  # 左上
                    [1.0, -1.0, 1.0, 0.0],  # 右下
                    [1.0, 1.0, 1.0, 1.0],  # 右上
                ],
                dtype=np.float32,
            ).tobytes()
        )

        self.vao = self.ctx.vertex_array(self.prog, [(self.vbo, '2f 2f', 'in_pos', 'in_texcoord')])

        # 用于渲染蒙板形状的辅助 VItem
        self._mask_vitem = VItem(stroke_alpha=0, fill_alpha=1)
        self._mask_vitem_renderer = self._mask_vitem.renderer_cls()

    def _render_mask_shape(self, item: ShapeMask) -> None:
        """将蒙版形状渲染为白色填充到 fbo_mask"""
        # 同步数据
        vitem = self._mask_vitem
        vitem.points.become(item.points)  # .points.become 中已有对重复设置的优化
        vitem._fix_in_frame = item._fix_in_frame

        # 渲染
        self._mask_vitem_renderer.render(vitem)

    def render(self, item: ShapeMask) -> None:
        if not self.initialized:
            self.init()
            self.initialized = True

        # 渲染影响物件到 fbo_content
        with blend_context(self.ctx, False), framebuffer_context(self.fbo_content):
            self.fbo_content.clear()
            gl.glFlush()

            item._render_collection.render(False)

        # 渲染蒙版形状到 fbo_mask
        with blend_context(self.ctx, False), framebuffer_context(self.fbo_mask):
            self.fbo_mask.clear()
            gl.glFlush()
            self._render_mask_shape(item)
            gl.glFlush()

        # 合成输出
        self.fbo_content.color_attachments[0].use(0)
        self.fbo_mask.color_attachments[0].use(1)

        self.u_content_tex.value = 0
        self.u_mask_tex.value = 1

        self.prog['u_mask_alpha'] = item.alpha._value
        self.prog['u_feather'] = item.feather._value
        self.prog['u_invert'] = item.invert._value

        self.vao.render(mgl.TRIANGLE_STRIP)
