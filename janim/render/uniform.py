from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable

import moderngl as mgl
from janim_backend import gl

from janim.render.base import get_programs

type UniformSetter = tuple[Callable, Any]
type UniformSetters = dict[str, UniformSetter]

_uniforms_ctxvar_of_mglctxs: dict[mgl.Context, ContextVar[UniformSetters]] = {}
"""
各个 ``mgl.Context`` 所对应的 uniform 上下文
"""

type UniformObjects = dict[str, gl.FastUniform]

_extracted_prog_uniforms: dict[mgl.Program | mgl.ComputeShader, UniformObjects] = {}
"""
各个 ``mgl.Program`` 所带有的 uniforms
"""

_janim_global_uniforms_information = {
    'JA_CAMERA_SCALED_FACTOR': gl.GL_FLOAT,
    'JA_CAMERA_CENTER': gl.GL_FLOAT_VEC3,
    'JA_CAMERA_LOC': gl.GL_FLOAT_VEC3,
    'JA_CAMERA_RIGHT': gl.GL_FLOAT_VEC3,
    'JA_CAMERA_UP': gl.GL_FLOAT_VEC3,
    'JA_VIEW_MATRIX': gl.GL_FLOAT_MAT4,
    'JA_FIXED_DIST_FROM_PLANE': gl.GL_FLOAT,
    'JA_PROJ_MATRIX': gl.GL_FLOAT_MAT4,
    'JA_FRAME_RADIUS': gl.GL_FLOAT_VEC2,
    'JA_ANTI_ALIAS_RADIUS': gl.GL_FLOAT,
    'JA_LIGHT_SOURCE': gl.GL_FLOAT_VEC3,
}
"""
JAnim 的所有全局 uniform 的注册信息

对应的 GLSL 文件： ``janim/render/includes/janim_globals.glsl``
"""


def _get_uniforms_context_var(ctx: mgl.Context) -> ContextVar[dict]:
    ctxvar = _uniforms_ctxvar_of_mglctxs.get(ctx, None)
    if ctxvar is None:
        ctxvar = _uniforms_ctxvar_of_mglctxs[ctx] = ContextVar(f'uniforms_{id(ctx)}', default={})
    return ctxvar


def _extract_uniform_objects(prog: mgl.Program | mgl.ComputeShader) -> UniformObjects:
    cache = _extracted_prog_uniforms.get(prog, None)
    if cache is not None:
        return cache

    prog_glo = prog.glo
    objects = {
        name: gl.FastUniform(prog_glo, name, gl_type)
        for name, gl_type in _janim_global_uniforms_information.items()
        if name in prog._members
    }
    _extracted_prog_uniforms[prog] = objects

    return objects


def apply_uniforms(
    prog: mgl.Program | mgl.ComputeShader, uniforms: UniformSetters | None = None
) -> None:
    if uniforms is None:
        uniforms = _get_uniforms_context_var(prog.ctx).get()
    prog_uniforms = _extract_uniform_objects(prog)

    for name in uniforms.keys() & prog_uniforms.keys():
        (setter_fn, setter_arg) = uniforms[name]
        uniform = prog_uniforms[name]

        setter_fn(uniform, setter_arg)


@contextmanager
def uniforms(ctx: mgl.Context, **kwargs: UniformSetter):
    ctxvar = _get_uniforms_context_var(ctx)

    old_uniforms = ctxvar.get()
    new_uniforms = old_uniforms.copy()
    new_uniforms.update(kwargs)

    reset_uniforms = {
        key: old_uniforms[key]  #
        for key in new_uniforms.keys() & old_uniforms.keys()
    }

    for prog in get_programs(ctx):
        apply_uniforms(prog, kwargs)

    token = ctxvar.set(new_uniforms)

    try:
        yield
    finally:
        ctxvar.reset(token)

        for prog in get_programs(ctx):
            apply_uniforms(prog, reset_uniforms)
