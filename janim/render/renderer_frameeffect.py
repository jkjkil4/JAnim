from __future__ import annotations

from typing import TYPE_CHECKING

import moderngl as mgl
import numpy as np
import OpenGL.GL as gl

from janim.anims.animation import Animation
from janim.render.base import Renderer
from janim.render.framebuffer import (blend_context, create_framebuffer,
                                      framebuffer_context)
from janim.render.program import get_program_from_string
from janim.utils.config import Config

if TYPE_CHECKING:
    from janim.items.frame_effect import FrameEffect


vertex_shader = '''
#version 330 core

in vec2 in_texcoord;

out vec2 v_texcoord;

void main()
{
    gl_Position = vec4(in_texcoord * 2.0 - 1.0, 0.0, 1.0);
    v_texcoord = in_texcoord;
}
'''


class FrameEffectRenderer(Renderer):
    def __init__(self):
        self.initialized: bool = False

    def init(self, fragment_shader: str, cache_key: str) -> None:
        self.ctx = Renderer.data_ctx.get().ctx
        self.prog = get_program_from_string(
            vertex_shader,
            fragment_shader,
            cache_key=cache_key
        )

        self.u_fbo = self.prog.get('fbo', None)
        if self.u_fbo is not None:
            self.u_fbo.value = 0

        self.fbo = create_framebuffer(self.ctx, Config.get.pixel_width, Config.get.pixel_height)
        self.vbo_texcoords = self.ctx.buffer(
            data=np.array([
                [0.0, 0.0],     # 左上
                [0.0, 1.0],     # 左下
                [1.0, 0.0],     # 右上
                [1.0, 1.0]      # 右下
            ], dtype=np.float32).tobytes()
        )

        self.vao = self.ctx.vertex_array(
            self.prog,
            self.vbo_texcoords,
            'in_texcoord'
        )

    def render(self, item: FrameEffect) -> None:
        if not self.initialized:
            self.init(item.fragment_shader, item.cache_key)
            self.initialized = True

        if self.u_fbo is not None:
            t = Animation.global_t_ctx.get()

            with blend_context(self.ctx, False), framebuffer_context(self.fbo):
                self.fbo.clear()
                # 为了颜色能被正确渲染到透明 framebuffer 上
                # 这里需要禁用自带 blending 的并使用 shader 里自定义的 blending（参考 program.py 的 injection_ja_finish_up）
                # 但是 shader 里的 blending 依赖 framebuffer 信息
                # 所以这里需要使用 glFlush 更新 framebuffer 信息使得正确渲染
                gl.glFlush()
                render_datas = [
                    (appr, appr.stack.compute(t, True))
                    for appr in item.apprs
                    if appr.is_visible_at(t)
                ]
                render_datas.sort(key=lambda x: x[1].depth, reverse=True)
                for appr, data in render_datas:
                    appr.render(data)
                    # 向透明 framebuffer 绘制时，每次都需要使用 glFlush 更新 framebuffer 信息使得正确渲染
                    gl.glFlush()

            self.fbo.color_attachments[0].use(0)

        for key, value in item._uniforms.items():
            self.prog[key] = value
        for key, value in item._optional_uniforms.items():
            if key in self.prog._members:
                self.prog[key] = value
        for key, value in item.dynamic_uniforms().items():
            self.prog[key] = value

        self.vao.render(mgl.TRIANGLE_STRIP)
