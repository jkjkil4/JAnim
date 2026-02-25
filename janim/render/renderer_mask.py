from __future__ import annotations

import itertools as it
from typing import TYPE_CHECKING

import moderngl as mgl
import numpy as np
import OpenGL.GL as gl

from janim.anims.animation import Animation
from janim.render.base import Renderer
from janim.render.framebuffer import (blend_context, create_framebuffer,
                                      framebuffer_context)
from janim.render.program import get_program_from_file_prefix
from janim.utils.config import Config

if TYPE_CHECKING:
    from janim.items.mask import Mask


class MaskRenderer(Renderer):
    """蒙版渲染器

    - ``fbo_content``: 渲染被遮罩物件的内容
    - ``fbo_mask``: 渲染蒙版形状（白色填充）

    通过 ``mask_compose`` 着色器将两者合成输出
    """
    def __init__(self):
        self.initialized: bool = False
        self._mask_vitem = None
        self._mask_vitem_renderer = None

    def init(self, item: Mask) -> None:
        self.ctx = Renderer.data_ctx.get().ctx
        pw, ph = Config.get.pixel_width, Config.get.pixel_height

        # 双 FBO
        self.fbo_content = create_framebuffer(self.ctx, pw, ph)
        self.fbo_mask = create_framebuffer(self.ctx, pw, ph)

        # 合成着色器
        self.prog = get_program_from_file_prefix("render/shaders/mask_compose")

        self.u_content_tex = self.prog.get("content_tex", None)
        self.u_mask_tex = self.prog.get("mask_tex", None)
        if self.u_content_tex is not None:
            self.u_content_tex.value = 0
        if self.u_mask_tex is not None:
            self.u_mask_tex.value = 1

        # 全屏四边形 VBO（in_pos + in_texcoord 交错）
        self.vbo = self.ctx.buffer(
            data=np.array([
                # in_pos        in_texcoord
                [-1.0, -1.0,    0.0, 0.0],     # 左下
                [-1.0,  1.0,    0.0, 1.0],     # 左上
                [ 1.0, -1.0,    1.0, 0.0],     # 右下
                [ 1.0,  1.0,    1.0, 1.0],     # 右上
            ], dtype=np.float32).tobytes()
        )

        self.vao = self.ctx.vertex_array(
            self.prog,
            [(self.vbo, "2f 2f", "in_pos", "in_texcoord")]
        )

    def _ensure_mask_vitem(self, item: Mask):
        """延迟创建用于渲染蒙版形状的辅助 VItem"""
        if self._mask_vitem is None:
            from janim.items.vitem import VItem
            from janim.render.renderer_vitem import VItemRenderer

            self._mask_vitem = VItem()
            self._mask_vitem._fix_in_frame = item._fix_in_frame
            self._mask_vitem_renderer = VItemRenderer()

    def _render_mask_shape(self, item: Mask) -> None:
        """将蒙版形状渲染为白色填充到 fbo_mask"""
        self._ensure_mask_vitem(item)

        vitem = self._mask_vitem
        # 同步点数据
        vitem.points.become(item.points)
        # 设置为白色填充，无描边
        vitem.fill.set([1.0, 1.0, 1.0], 1.0, root_only=True)
        vitem.stroke.set(alpha=0.0, root_only=True)
        vitem._fix_in_frame = item._fix_in_frame

        self._mask_vitem_renderer.render(vitem)

    def render(self, item: Mask) -> None:
        if not self.initialized:
            self.init(item)
            self.initialized = True

        t = Animation.global_t_ctx.get()

        # 渲染受影响物件到 fbo_content
        with blend_context(self.ctx, False), framebuffer_context(self.fbo_content):
            self.fbo_content.clear()
            gl.glFlush()

            items_render = [
                (appr.stack.compute(t, True), appr.render)
                for appr in item._affected_apprs
                if appr.is_visible_at(t)
            ]
            items_render.extend(it.chain(*item._additional_lists))

            items_render.sort(key=lambda x: x[0].depth, reverse=True)

            for data, render in items_render:
                render(data)
                gl.glFlush()

        # 渲染蒙版形状到 fbo_mask
        with blend_context(self.ctx, False), framebuffer_context(self.fbo_mask):
            self.fbo_mask.clear()
            gl.glFlush()
            self._render_mask_shape(item)
            gl.glFlush()

        # 合成输出
        self.fbo_content.color_attachments[0].use(0)
        self.fbo_mask.color_attachments[0].use(1)

        pw, ph = Config.get.pixel_width, Config.get.pixel_height

        if "u_mask_alpha" in self.prog._members:
            self.prog["u_mask_alpha"] = item.mask_alpha._value
        if "u_feather" in self.prog._members:
            self.prog["u_feather"] = item.feather._value
        if "u_invert" in self.prog._members:
            self.prog["u_invert"] = item.invert._value
        if "u_tex_size" in self.prog._members:
            self.prog["u_tex_size"] = (float(pw), float(ph))

        self.vao.render(mgl.TRIANGLE_STRIP)
