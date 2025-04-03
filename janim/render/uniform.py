
from contextlib import contextmanager
from contextvars import ContextVar

import moderngl as mgl

from janim.render.base import get_programs

uniforms_map: dict[mgl.Context, ContextVar[dict]] = {}


def get_uniforms_context_var(ctx: mgl.Context) -> ContextVar[dict]:
    ctxvar = uniforms_map.get(ctx, None)
    if ctxvar is None:
        ctxvar = uniforms_map[ctx] = ContextVar(f'uniforms_{id(ctx)}', default=dict(JA_BLENDING=False))
    return ctxvar


def apply_uniforms(prog: mgl.Program | mgl.ComputeShader, uniforms: dict | None = None) -> None:
    if uniforms is None:
        uniforms = get_uniforms_context_var(prog.ctx).get()
    for key, value in uniforms.items():
        if key in prog._members:
            prog[key] = value


@contextmanager
def uniforms(ctx: mgl.Context, **kwargs):
    ctxvar = get_uniforms_context_var(ctx)

    old_value = ctxvar.get()
    new_value = old_value.copy()
    new_value.update(kwargs)
    diff = {
        key: old_value[key]
        for key in new_value.keys() & old_value.keys()
    }

    for prog in get_programs(ctx):
        apply_uniforms(prog, kwargs)

    token = ctxvar.set(new_value)

    try:
        yield
    finally:
        ctxvar.reset(token)

        for prog in get_programs(ctx):
            apply_uniforms(prog, diff)
