from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import moderngl as mgl
import numpy as np

from janim.camera.camera_info import CameraInfo
from janim.locale.i18n import get_local_strings
from janim.utils.iterables import resize_with_interpolation

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

    @staticmethod
    def update_dynamic_buffer_data(
        new_data: np.ndarray,
        vbo: mgl.Buffer,
        resize_target: int,
        use_32byte_align: bool = False
    ) -> None:
        processed_data = resize_with_interpolation(new_data, resize_target)
        assert processed_data.dtype == np.float32
        bytes_data = processed_data.tobytes()

        size = (
            ((len(bytes_data) + 31) & ~31)
            if use_32byte_align
            else len(bytes_data)
        )
        if size != vbo.size:
            vbo.orphan(size)

        vbo.write(bytes_data)

    @staticmethod
    def update_static_buffer_data(
        new_data: np.ndarray,
        vbo: mgl.Buffer,
        resize_target: int
    ) -> None:
        processed_data = resize_with_interpolation(new_data, resize_target)
        assert processed_data.dtype == np.float32
        bytes_data = processed_data.tobytes()

        assert len(bytes_data) == vbo.size

        vbo.write(bytes_data)

    @staticmethod
    @contextmanager
    def depth_test_if_enabled(ctx: mgl.Context, item: Item):
        if item._depth_test:
            ctx.enable(mgl.DEPTH_TEST)
            try:
                yield
            finally:
                ctx.disable(mgl.DEPTH_TEST)
        else:
            yield


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
