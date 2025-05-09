from __future__ import annotations

import weakref
from contextlib import contextmanager

import moderngl as mgl

from janim.render.uniform import get_uniforms_context_var, uniforms
from janim.typing import TYPE_CHECKING

if TYPE_CHECKING:
    from janim.gui.glwidget import GLWidget

FRAME_BUFFER_BINDING = 15

_qt_glwidget_ref: dict[mgl.Context, weakref.ReferenceType[GLWidget]] = {}


def register_qt_glwidget(w: GLWidget) -> None:
    _qt_glwidget_ref[w.ctx] = weakref.ref(w)


def get_qt_glwidget(ctx: mgl.Context) -> GLWidget | None:
    ref = _qt_glwidget_ref.get(ctx, None)
    return None if ref is None else ref()


def create_framebuffer(ctx: mgl.Context, pw: int, ph: int) -> mgl.Framebuffer:
    _qt_glwidget = get_qt_glwidget(ctx)

    on_qt = _qt_glwidget is not None
    if on_qt:
        prev = _qt_glwidget.qfuncs.glGetIntegerv(0x8CA6)   # GL_FRAMEBUFFER_BINDING

    fbo = ctx.framebuffer(
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

    if on_qt and prev == _qt_glwidget.defaultFramebufferObject():
        # 如果这里不调用 glBindFramebuffer，PyOpenGL 会出现 invalid framebuffer operation 的报错
        # 这里通过 qt 调用 OpenGL 函数，把 framebuffer bind 回先前的就好了
        # 推测可能是因为 moderngl、PyOpenGL、QtOpenGL 的一些状态没有同步
        # 下面 framebuffer_context 中的处理与这同理
        _qt_glwidget.qfuncs.glBindFramebuffer(0x8D40, prev)     # GL_FRAMEBUFFER
        ratio = _qt_glwidget.devicePixelRatio()
        _qt_glwidget.qfuncs.glViewport(0, 0, int(_qt_glwidget.width() * ratio), int(_qt_glwidget.height() * ratio))
        _qt_glwidget.update_clear_color()

    return fbo


@contextmanager
def framebuffer_context(fbo: mgl.Framebuffer):
    _qt_glwidget = get_qt_glwidget(fbo.ctx)

    on_qt = _qt_glwidget is not None
    if on_qt:
        prev = _qt_glwidget.qfuncs.glGetIntegerv(0x8CA6)   # GL_FRAMEBUFFER_BINDING

    prev_fbo = fbo.ctx.fbo
    fbo.use()
    fbo.color_attachments[0].use(FRAME_BUFFER_BINDING)
    try:
        yield
    finally:
        if prev_fbo is not None:
            prev_fbo.use()

        if on_qt and prev == _qt_glwidget.defaultFramebufferObject():
            # 这里的处理，请参考 create_framebuffer 中对应部分的注释
            _qt_glwidget.qfuncs.glBindFramebuffer(0x8D40, prev)     # GL_FRAMEBUFFER
            ratio = _qt_glwidget.devicePixelRatio()
            _qt_glwidget.qfuncs.glViewport(0, 0, int(_qt_glwidget.width() * ratio), int(_qt_glwidget.height() * ratio))
            _qt_glwidget.update_clear_color()
        elif prev_fbo is not None:
            prev_fbo.color_attachments[0].use(FRAME_BUFFER_BINDING)


@contextmanager
def blend_context(ctx: mgl.Context, on: bool):
    blending = get_uniforms_context_var(ctx).get().get('JA_BLENDING')
    if on == blending:
        yield
        return

    blending = not blending
    (ctx.enable if blending else ctx.disable)(mgl.BLEND)
    try:
        with uniforms(ctx, JA_BLENDING=blending):
            yield
    finally:
        blending = not blending
        (ctx.enable if blending else ctx.disable)(mgl.BLEND)
