from __future__ import annotations

import moderngl as mgl
import numpy as np

from janim.render.framebuffer import FrameBuffer, qt_framebuffer_patch


class MotionBlurBuffer:
    """Accumulate independent premultiplied scene samples in a float texture.

    Samples are rendered into an offscreen framebuffer and added into a floating
    point accumulation texture. The final average is drawn onto whichever
    framebuffer is currently bound by the caller, so the same code works for the
    Qt widget, ``capture`` and ``VideoWriter``.
    """

    def __init__(self, ctx: mgl.Context, size: tuple[int, int]):
        self.ctx = ctx
        self.size = size
        self.sample = FrameBuffer(ctx, *size, (0, 0, 0), True)
        with qt_framebuffer_patch(ctx):
            self.accumulation = ctx.framebuffer(
                color_attachments=ctx.texture(size, components=4, dtype='f4')
            )
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
        # ``Framebuffer.clear`` changes the active framebuffer.  In the Qt
        # preview the caller owns the widget framebuffer, so preserve it just
        # like ``FrameBuffer.context`` does for scene samples.
        with qt_framebuffer_patch(self.ctx):
            prev_fbo = self.ctx.fbo
            try:
                self.accumulation.clear(0, 0, 0, 0)
            finally:
                if prev_fbo is not None:
                    prev_fbo.use()

    def add_sample(self) -> None:
        with qt_framebuffer_patch(self.ctx):
            prev_fbo = self.ctx.fbo
            self.sample.use(0)
            self.accumulation.use()
            try:
                self.ctx.disable(mgl.DEPTH_TEST)
                self.ctx.enable(mgl.BLEND)
                self.ctx.blend_func = mgl.ONE, mgl.ONE
                self.program['weight'] = 1.0
                self.vao.render(mgl.TRIANGLE_STRIP)
            finally:
                self.ctx.blend_func = mgl.ONE, mgl.ONE_MINUS_SRC_ALPHA
                if prev_fbo is not None:
                    prev_fbo.use()

    def resolve(self, count: int) -> None:
        """Draw the averaged result onto the currently bound framebuffer."""
        with qt_framebuffer_patch(self.ctx):
            prev_fbo = self.ctx.fbo
            try:
                self.accumulation.color_attachments[0].use(0)
                self.ctx.disable(mgl.DEPTH_TEST)
                self.ctx.enable(mgl.BLEND)
                self.ctx.blend_func = mgl.ONE, mgl.ONE_MINUS_SRC_ALPHA
                self.program['weight'] = 1.0 / count
                self.vao.render(mgl.TRIANGLE_STRIP)
            finally:
                if prev_fbo is not None:
                    prev_fbo.use()

    def release(self) -> None:
        self.sample._fbo.color_attachments[0].release()
        self.sample._fbo.depth_attachment.release()
        self.sample.release()
        self.accumulation.color_attachments[0].release()
        self.accumulation.release()
        self.vertices.release()
        self.vao.release()
        self.program.release()
