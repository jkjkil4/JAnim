from __future__ import annotations

import moderngl as mgl
import numpy as np

from janim.render.base import DEFAULT_BLEND_FUNC
from janim.render.framebuffer import FrameBuffer


class MotionBlurBuffer:
    """将各次采样的完整场景累加到浮点纹理中

    各样本先渲染到离屏 framebuffer，再以预乘透明度累加进浮点累积纹理。
    最终平均值会被绘制到调用方当前绑定的 framebuffer 上
    """

    def __init__(self, ctx: mgl.Context, size: tuple[int, int]):
        self.ctx = ctx
        self.size = size
        self.sample = FrameBuffer(ctx, *size, (0, 0, 0), True)
        self.accumulation = FrameBuffer(ctx, *size, (0, 0, 0), True, no_clip=True)

        self.program = ctx.program(
            vertex_shader="""
                #version 330 core
                in vec2 in_coord;
                out vec2 uv;
                void main() {
                    uv = in_coord;
                    gl_Position = vec4(in_coord * 2.0 - 1.0, 0.0, 1.0);
                }
            """,
            fragment_shader="""
                #version 330 core
                in vec2 uv;
                out vec4 color;
                uniform sampler2D source;
                uniform float weight;
                void main() {
                    color = texture(source, uv) * weight;
                }
            """,
        )

        vertices = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=np.float32)
        self.vertices = ctx.buffer(vertices.tobytes())
        self.vao = ctx.vertex_array(self.program, [(self.vertices, '2f', 'in_coord')])
        self.program['source'] = 0

    def clear(self) -> None:
        self.accumulation.clear()

    def add_sample(self) -> None:
        with self.accumulation.context():
            self.sample.use(0)
            try:
                self.ctx.blend_func = mgl.ONE, mgl.ONE
                self.program['weight'] = 1.0
                self.vao.render(mgl.TRIANGLE_STRIP)
            finally:
                self.ctx.blend_func = DEFAULT_BLEND_FUNC

    def resolve(self, count: int) -> None:
        """将平均后的结果绘制到当前绑定的 framebuffer 上"""
        self.accumulation.use(0)
        self.program['weight'] = 1.0 / count
        self.vao.render(mgl.TRIANGLE_STRIP)

    def release(self) -> None:
        self.sample.release()
        self.accumulation.release()
        self.vertices.release()
        self.vao.release()
        self.program.release()
