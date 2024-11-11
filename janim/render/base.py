from __future__ import annotations

import os
from collections import defaultdict
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import moderngl as mgl

from janim.camera.camera_info import CameraInfo
from janim.utils.file_ops import find_file, get_janim_dir, readall

if TYPE_CHECKING:
    from janim.items.item import Item

FIX_IN_FRAME_KEY = 'JA_FIX_IN_FRAME'


class Renderer:
    '''渲染器的基类

    重写 :meth:`init` 和 :meth:`render` 以实现具体功能
    '''
    data_ctx: ContextVar[RenderData] = ContextVar('Renderer.data_ctx')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initialized = False

    def init(self) -> None: ...

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

    def find_shader(filepath: str) -> str | None:
        try:
            return find_file(filepath)
        except FileNotFoundError:
            return None

    prog = ctx.program(**{
        shader_type: readall(_shader_path)
        for shader_type, suffix in shader_keys
        if (_shader_path := find_shader(filepath + suffix)) is not None
    })

    global_uniforms = global_uniform_map.get(ctx, None)
    if global_uniforms is not None:
        apply_global_uniforms(global_uniforms, prog)

    ctx_program_map[filepath] = prog
    return prog


def get_compute_shader(filepath: str) -> mgl.ComputeShader:
    '''
    载入指定文件的 ComputeShader，
    例如 `render/shaders/map_points.comp.glsl` 就会载入这个文件

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
