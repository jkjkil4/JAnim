from __future__ import annotations

from collections import defaultdict
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import moderngl as mgl

from janim.camera.camera_info import CameraInfo
from janim.locale.i18n import get_local_strings

if TYPE_CHECKING:
    from janim.items.item import Item

_ = get_local_strings('base')

FIX_IN_FRAME_KEY = 'JA_FIX_IN_FRAME'


@dataclass
class Programs:
    cache: dict[Any, mgl.Program | mgl.ComputeShader] = field(default_factory=lambda: {})
    additional: list[mgl.Program] = field(default_factory=lambda: [])


programs_map: defaultdict[mgl.Context, Programs] = defaultdict(Programs)


def get_programs(ctx: mgl.Context):
    programs = programs_map[ctx]
    yield from programs.cache.values()
    yield from programs.additional


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


def create_context(**kwargs) -> mgl.Context:
    ctx = mgl.create_context(**kwargs)
    # 默认是 blend-off 的
    ctx.blend_func = (
        mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA,
        mgl.ONE, mgl.ONE
    )
    ctx.blend_equation = mgl.FUNC_ADD, mgl.MAX
    return ctx
