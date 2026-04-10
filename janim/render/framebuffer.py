from __future__ import annotations

import weakref
from contextlib import contextmanager
from functools import lru_cache

import moderngl as mgl
import numpy as np
from PIL import Image

from janim.typing import TYPE_CHECKING

if TYPE_CHECKING:
    from janim.gui.glwidget import GLWidget

_qt_glwidget_ref: dict[mgl.Context, weakref.ReferenceType[GLWidget]] = {}


def register_qt_glwidget(w: GLWidget) -> None:
    _qt_glwidget_ref[w.ctx] = weakref.ref(w)


def get_qt_glwidget(ctx: mgl.Context) -> GLWidget | None:
    ref = _qt_glwidget_ref.get(ctx, None)
    return None if ref is None else ref()


@contextmanager
def qt_framebuffer_patch(ctx: mgl.Context):
    """
    对 :meth:`~.GLWidget.use_qt_framebuffer` 的进一步封装，自动在 with 前获取 GL 对象，在 with 后重设 GL 对象（如果是 Qt 的 Framebuffer）
    """
    _qt_glwidget = get_qt_glwidget(ctx)
    if _qt_glwidget is None:
        yield
        return

    prev = _qt_glwidget.qfuncs.glGetIntegerv(0x8CA6)   # GL_FRAMEBUFFER_BINDING
    try:
        yield
    finally:
        if prev == _qt_glwidget.defaultFramebufferObject():
            # 如果这里不调用 glBindFramebuffer，PyOpenGL 会出现 invalid framebuffer operation 的报错
            # 这里通过 qt 调用 OpenGL 函数，把 framebuffer bind 回先前的就好了
            # 推测可能是因为 moderngl、PyOpenGL、QtOpenGL 的一些状态没有同步
            _qt_glwidget.qfuncs.glBindFramebuffer(0x8D40, prev)     # GL_FRAMEBUFFER
            ratio = _qt_glwidget.devicePixelRatio()
            _qt_glwidget.qfuncs.glViewport(0, 0, int(_qt_glwidget.width() * ratio), int(_qt_glwidget.height() * ratio))
            _qt_glwidget.update_clear_color()


class FrameBuffer:
    def __init__(self, ctx: mgl.Context, pw: int, ph: int, rgb: tuple[int, int, int], transparent: bool):
        self._clear_params = (*rgb, float(not transparent))
        self._transparent = transparent

        self.ctx = ctx
        self._fbo = self._create_framebuffer(ctx, pw, ph)

    @staticmethod
    def _create_framebuffer(ctx: mgl.Context, pw: int, ph: int) -> mgl.Framebuffer:
        with qt_framebuffer_patch(ctx):
            return ctx.framebuffer(
                color_attachments=ctx.texture(
                    (pw, ph),
                    components=4,
                    samples=0,
                ),
                depth_attachment=ctx.depth_renderbuffer(
                    (pw, ph),
                    samples=0
                )
            )

    def clear(self) -> None:
        self._fbo.clear(*self._clear_params)

    @contextmanager
    def context(self):
        with qt_framebuffer_patch(self.ctx):
            prev_fbo = self.ctx.fbo
            self._fbo.use()
            try:
                yield
            finally:
                if prev_fbo is not None:
                    prev_fbo.use()

    def unpremultiply(self) -> None:
        """将当前 FBO 的 PMA 内容通过 GPU pass 转为 straight alpha，结果写回自身"""
        if not self._transparent:
            return

        prog, vao = self._get_unpremultiply_vao(self.ctx)
        unpma_fbo = self._get_unpremultiply_fbo(self.ctx, self._fbo.size)

        # 绑定源纹理并执行转换
        self._fbo.color_attachments[0].use(0)
        prog['tex'] = 0
        unpma_fbo.use()
        self.ctx.disable(mgl.BLEND)
        vao.render(mgl.TRIANGLE_STRIP)
        self.ctx.enable(mgl.BLEND)

        # 把转换结果复制回原 FBO
        self.ctx.copy_framebuffer(self._fbo, unpma_fbo)
        self._fbo.use()     # 这里假设了调用该方法前活跃的就是 self._fbo，所以这里重新让它 use

    @staticmethod
    @lru_cache(maxsize=8)
    def _get_unpremultiply_vao(ctx: mgl.Context):
        """获取 unpremultiply shader 程序和 VAO"""
        prog = ctx.program(
            R'''
            #version 330 core

            in vec2 in_coord;
            out vec2 v_coord;

            void main()
            {
                gl_Position = vec4(in_coord * 2.0 - 1.0, 0.0, 1.0);
                v_coord = in_coord;
            }
            ''',
            R'''
            #version 330 core

            in vec2 v_coord;
            out vec4 out_color;

            uniform sampler2D tex;

            void main()
            {
                vec4 pma = texture(tex, v_coord);
                if (pma.a > 0.0) {
                    out_color = vec4(pma.rgb / pma.a, pma.a);
                } else {
                    out_color = vec4(0.0);
                }
            }
            '''
        )

        # 构建全屏四边形 VAO
        vbo = ctx.buffer(
            data=np.array([
                [0.0, 0.0],
                [0.0, 1.0],
                [1.0, 0.0],
                [1.0, 1.0]
            ], dtype=np.float32).tobytes()
        )
        vao = ctx.vertex_array(prog, [(vbo, '2f', 'in_coord')])

        return prog, vao

    @staticmethod
    @lru_cache(maxsize=8)
    def _get_unpremultiply_fbo(ctx: mgl.Context, size: tuple[int, int]):
        return ctx.framebuffer(
            color_attachments=ctx.texture(
                size,
                components=4,
                samples=0,
            )
        )

    def read(self) -> bytes:
        return self._fbo.read(components=4)

    def get_image(self) -> Image.Image:
        return Image.frombytes(
            'RGBA', self._fbo.size, self.read(),
            'raw', 'RGBA', 0, -1
        )

    def release(self) -> None:
        self._fbo.release()
