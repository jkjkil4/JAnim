from __future__ import annotations

from typing import TYPE_CHECKING

import moderngl as mgl
import numpy as np

from janim.render.base import Renderer
from janim.render.framebuffer import FrameBuffer
from janim.render.program import get_program_from_string
from janim.render.shader import shader_injections_ctx
from janim.utils.config import Config

if TYPE_CHECKING:
    from janim.items.effect.frame_effect import FrameEffect


vertex_shader = """
#version 330 core

in vec2 in_texcoord;

out vec2 v_texcoord;

void main()
{
    gl_Position = vec4(in_texcoord * 2.0 - 1.0, 0.0, 1.0);
    v_texcoord = in_texcoord;
}
"""


class FrameEffectRenderer(Renderer):
    def __init__(self):
        self.initialized: bool = False

    def init(self, item: FrameEffect) -> None:
        self.ctx = Renderer.data_ctx.get().ctx

        token = shader_injections_ctx.set(item.injections)
        try:
            self.prog = get_program_from_string(
                vertex_shader,
                item.fragment_shader,
                cache_key=item.cache_key,
                shader_name=item.__class__.__name__,
            )
        finally:
            shader_injections_ctx.reset(token)

        self.u_fbo = self.prog.get('_fbo', None)
        if self.u_fbo is not None:
            self.u_fbo.value = 0

        self.framebuffer = FrameBuffer(
            self.ctx, Config.get.pixel_width, Config.get.pixel_height, (0, 0, 0), True
        )
        self.vbo_texcoords = self.ctx.buffer(
            data=np.array(
                [
                    [0.0, 0.0],  # 左上
                    [0.0, 1.0],  # 左下
                    [1.0, 0.0],  # 右上
                    [1.0, 1.0],  # 右下
                ],
                dtype=np.float32,
            ).tobytes()
        )

        self.vao = self.ctx.vertex_array(self.prog, self.vbo_texcoords, 'in_texcoord')

    def render(self, item: FrameEffect) -> None:
        if not self.initialized:
            self.init(item)
            self.initialized = True

        if self.u_fbo is not None:
            with self.framebuffer.context():
                self.framebuffer.clear()
                item._render_collection.render()

            self.framebuffer.use(0)

        for key, value in item._uniforms.items():
            self.prog[key] = value
        for key, value in item._optional_uniforms.items():
            if key in self.prog._members:
                self.prog[key] = value
        for key, value in item.dynamic_uniforms().items():
            self.prog[key] = value

        self.vao.render(mgl.TRIANGLE_STRIP)
