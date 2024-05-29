from __future__ import annotations

import os
from contextvars import ContextVar
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import moderngl as mgl

from janim.camera.camera_info import CameraInfo
from janim.utils.file_ops import get_janim_dir, readall

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
    def update_fix_in_frame(item: Item, prog: mgl.Program):
        if FIX_IN_FRAME_KEY in prog._members:
            prog[FIX_IN_FRAME_KEY] = item._fix_in_frame


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
program_map: defaultdict[mgl.Context, dict[str, mgl.Program]] = defaultdict(dict)


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
    给定文件位置自动遍历后缀并读取着色器代码，
    例如传入 `shaders/dotcloud` 后，会自动读取以下位置的代码：

    - shaders/dotcloud.vert
    - shaders/dotcloud.geom
    - shaders/dotcloud.frag

    若没有则缺省，但要能创建可用的着色器

    注：若 ``filepath`` 对应着色器程序先前已创建过，则会复用先前的对象，否则另外创建新的对象并记录
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
