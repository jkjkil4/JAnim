from __future__ import annotations

import os
from collections import defaultdict
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import moderngl as mgl

from janim.camera.camera_info import CameraInfo
from janim.exception import EXITCODE_PYOPENGL_NOT_FOUND, ExitException
from janim.locale.i18n import get_local_strings
from janim.utils.file_ops import find_file_or_none, get_janim_dir, readall

if TYPE_CHECKING:
    from janim.gui.glwidget import GLWidget
    from janim.items.item import Item

_ = get_local_strings('base')

FIX_IN_FRAME_KEY = 'JA_FIX_IN_FRAME'


def create_context(**kwargs) -> mgl.Context:
    ctx = mgl.create_context(**kwargs)
    check_pyopengl_if_required(ctx)
    ctx.enable(mgl.BLEND)
    ctx.blend_func = (
        mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA,
        mgl.ONE, mgl.ONE
    )
    ctx.blend_equation = mgl.FUNC_ADD, mgl.MAX
    return ctx


_qt_glwidget: GLWidget | None = None


def register_qt_glwidget(w: GLWidget) -> None:
    global _qt_glwidget
    _qt_glwidget = w


def create_framebuffer(ctx: mgl.Context, pw: int, ph: int) -> mgl.Framebuffer:
    on_qt = _qt_glwidget is not None and _qt_glwidget.ctx is ctx
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

    if on_qt and prev is _qt_glwidget.defaultFramebufferObject():
        # 如果这里不调用 glBindFramebuffer，PyOpenGL 会出现 invalid framebuffer operation 的报错
        # 这里通过 qt 调用 OpenGL 函数，把 framebuffer bind 回先前的就好了
        # 推测可能是因为 moderngl、PyOpenGL、QtOpenGL 的一些状态没有同步
        # 下面 framebuffer_context 中的处理与这同理
        _qt_glwidget.qfuncs.glBindFramebuffer(0x8D40, prev)     # GL_FRAMEBUFFER
        _qt_glwidget.qfuncs.glViewport(0, 0, _qt_glwidget.width(), _qt_glwidget.height())
        _qt_glwidget.update_clear_color()

    return fbo


@contextmanager
def framebuffer_context(fbo: mgl.Framebuffer):
    on_qt = _qt_glwidget is not None and _qt_glwidget.ctx is fbo.ctx
    if on_qt:
        prev = _qt_glwidget.qfuncs.glGetIntegerv(0x8CA6)   # GL_FRAMEBUFFER_BINDING

    prev_fbo = fbo.ctx.fbo
    fbo.use()
    try:
        yield
    finally:
        prev_fbo.use()

        if on_qt and prev is _qt_glwidget.defaultFramebufferObject():
            # 这里的处理，请参考 create_framebuffer 中对应部分的注释
            _qt_glwidget.qfuncs.glBindFramebuffer(0x8D40, prev)     # GL_FRAMEBUFFER
            _qt_glwidget.qfuncs.glViewport(0, 0, _qt_glwidget.width(), _qt_glwidget.height())
            _qt_glwidget.update_clear_color()


class Renderer:
    '''渲染器的基类

    重写 :meth:`render` 以实现具体功能
    '''
    data_ctx: ContextVar[RenderData] = ContextVar('Renderer.data_ctx')

    def render(self, item) -> None: ...

    @staticmethod
    def get_u_fix_in_frame(prog: mgl.Program) -> mgl.Uniform:
        return prog[FIX_IN_FRAME_KEY]

    @staticmethod
    def update_fix_in_frame(uniform: mgl.Uniform, item: Item) -> None:
        uniform.value = item._fix_in_frame


@dataclass(kw_only=True)
class RenderData:
    '''在渲染过程中需要配置的属性

    通过 :py:obj:`Renderer.data_ctx` 进行设置和获取
    '''
    ctx: mgl.Context
    camera_info: CameraInfo
    anti_alias_radius: float


shader_keys = (
    ('vertex_shader', '.vert.glsl'),
    ('geometry_shader', '.geom.glsl'),
    ('fragment_shader', '.frag.glsl')
)

type UniformPair = tuple[str, Any]

global_uniform_map: dict[mgl.Context, list[UniformPair]] = {}
program_map: defaultdict[mgl.Context, dict[str, mgl.Program | mgl.ComputeShader]] = defaultdict(dict)


def set_global_uniforms(ctx: mgl.Context, *uniforms: UniformPair) -> None:
    '''
    设置在每个着色器中都可以访问到的 ``uniforms`` （需要在着色器中声明后使用）
    '''
    global_uniform_map[ctx] = uniforms
    for prog in program_map[ctx].values():
        apply_global_uniforms(uniforms, prog)


def apply_global_uniforms(uniforms: list[UniformPair], prog: mgl.Program) -> None:
    '''将 ``uniforms`` 设置到 ``prog`` 中，并且跳过 ``prog`` 中没有的属性'''
    for key, value in uniforms:
        if key in prog._members:
            prog[key] = value


def get_program(filepath: str) -> mgl.Program:
    '''
    给定相对于 janim 路径的文件位置，自动遍历后缀并读取着色器代码，
    例如传入 `render/shaders/dotcloud` 后，会自动读取以下位置的代码：

    - redner/shaders/dotcloud.vert
    - render/shaders/dotcloud.geom
    - render/shaders/dotcloud.frag

    若没有则缺省，但要能创建可用的着色器

    注：

    - 若 ``filepath`` 对应着色器程序先前已创建过，则会复用先前的对象，否则另外创建新的对象并记录
    - 该方法只能读取 janim 内置的着色器，读取自定义着色器请使用 :meth:`get_custom_program`
    '''
    ctx = Renderer.data_ctx.get().ctx
    ctx_program_map = program_map[ctx]

    prog = ctx_program_map.get(filepath, None)
    if prog is not None:
        return prog

    shader_path = os.path.join(get_janim_dir(), filepath)

    prog = ctx.program(**{
        shader_type: readall(shader_path + suffix)
        for shader_type, suffix in shader_keys
        if os.path.exists(shader_path + suffix)
    })

    global_uniforms = global_uniform_map.get(ctx, None)
    if global_uniforms is not None:
        apply_global_uniforms(global_uniforms, prog)

    ctx_program_map[filepath] = prog
    return prog


def get_custom_program(filepath: str) -> mgl.Program:
    '''
    给定文件位置自动遍历后缀并读取着色器代码，
    例如传入 `shaders/yourshader` 后，会自动读取以下位置的代码：

    - shaders/yourshader.vert
    - shaders/yourshader.geom
    - shaders/yourshader.frag

    若没有则缺省，但要能创建可用的着色器

    注：

    - 若 ``filepath`` 对应着色器程序先前已创建过，则会复用先前的对象，否则另外创建新的对象并记录
    - 该方法只能读取自定义的着色器，读取 janim 内置着色器请使用 :meth:`get_program`
    '''
    ctx = Renderer.data_ctx.get().ctx
    ctx_program_map = program_map[ctx]

    prog = ctx_program_map.get(filepath, None)
    if prog is not None:
        return prog

    prog = ctx.program(**{
        shader_type: readall(_shader_path)
        for shader_type, suffix in shader_keys
        if (_shader_path := find_file_or_none(filepath + suffix)) is not None
    })

    global_uniforms = global_uniform_map.get(ctx, None)
    if global_uniforms is not None:
        apply_global_uniforms(global_uniforms, prog)

    ctx_program_map[filepath] = prog
    return prog


def get_compute_shader(filepath: str) -> mgl.ComputeShader:
    '''
    载入相对于 janim 目录的指定文件的 ComputeShader，
    例如 `render/shaders/map_points.comp.glsl` 就会载入 janim 文件夹中的这个文件

    注：若 ``filepath`` 对应的 ComputeShader 先前已创建过，则会复用先前的对象，否则另外创建新的对象并记录
    '''
    ctx = Renderer.data_ctx.get().ctx
    ctx_program_map = program_map[ctx]

    comp = ctx_program_map.get(filepath, None)
    if comp is not None:
        return comp

    shader_path = os.path.join(get_janim_dir(), filepath)

    comp = ctx.compute_shader(readall(shader_path))

    global_uniforms = global_uniform_map.get(ctx, None)
    if global_uniforms is not None:
        apply_global_uniforms(global_uniforms, comp)

    ctx_program_map[filepath] = comp
    return comp


def check_pyopengl_if_required(ctx: mgl.Context) -> None:
    if ctx.version_code >= 430:
        return

    try:
        import OpenGL.GL as gl  # noqa: F401
    except ImportError:
        print(
            _('An additional module is required to be compatible with OpenGL {version} (lower than OpenGL 4.3), '
              'but it is not installed')
            .format(version=ctx.info['GL_VERSION'])
        )
        print(_('You can install it using "pip install PyOpenGL" '
                'and make sure you install it in the correct Python version'))
        raise ExitException(EXITCODE_PYOPENGL_NOT_FOUND)
