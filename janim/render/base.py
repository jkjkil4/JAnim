from __future__ import annotations

import os
from contextvars import ContextVar
from dataclasses import dataclass

import moderngl as mgl

from janim.camera.camera_info import CameraInfo
from janim.utils.file_ops import get_janim_dir, readall


class Renderer:
    data_ctx: ContextVar[RenderData] = ContextVar('Renderer.data_ctx')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initialized = False

    def init(self) -> None: ...

    def render(self, data) -> None: ...


@dataclass(kw_only=True)
class RenderData:
    ctx: mgl.Context
    camera_info: CameraInfo


shader_keys = (
    ('vertex_shader', '.vert.glsl'),
    ('geometry_shader', '.geom.glsl'),
    ('fragment_shader', '.frag.glsl')
)

program_map: dict[str, mgl.Program] = {}


def get_program(filepath: str) -> mgl.Program:
    '''
    给定文件位置自动遍历后缀并读取着色器代码，
    例如传入 `shaders/dotcloud` 后，会自动读取以下位置的代码：

    - `shaders/dotcloud.vert`
    - `shaders/dotcloud.geom`
    - `shaders/dotcloud.frag`

    若没有则缺省，但要能创建可用的着色器

    注：若 ``filepath`` 对应着色器程序先前已创建过，则会复用先前的对象，否则另外创建新的对象并记录
    '''
    prog = program_map.get(filepath, None)
    if prog is not None:
        return prog

    shader_path = os.path.join(get_janim_dir(), filepath)

    prog = Renderer.data_ctx.get().ctx.program(**{
        shader_type: readall(shader_path + suffix)
        for shader_type, suffix in shader_keys
        if os.path.exists(shader_path + suffix)
    })
    program_map[filepath] = prog
    return prog
