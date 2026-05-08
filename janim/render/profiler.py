import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterable

import OpenGL.GL as gl

from janim.anims.timeline import ItemWithRenderFunc
from janim.render.collection import RenderCollection


class RenderProfiler:
    """
    性能分析器

    用于 patch 物件渲染，统计物件渲染的耗时与性能
    """

    def __init__(self, *, max_history: int = 200):
        self.max_history = max_history
        self.history: deque[FrameRecord] = deque(maxlen=max_history)

    @contextmanager
    def record_frame(self):
        """
        在渲染顶层入口 ``with`` 该函数，统计内部代码块的物件用时，存入 ``history`` 中作为一帧的数据
        """
        t = time.perf_counter()
        item_times = defaultdict(float)
        try:
            with self._patch_collection_render(item_times):
                yield
        finally:
            elapsed = time.perf_counter() - t
            self.history.append(FrameRecord(t, elapsed, item_times))

    @staticmethod
    @contextmanager
    def _patch_collection_render(item_times: dict[str, float]):
        # 由于渲染的嵌套结构，会出现 record 中途进入另一个 record 的情况
        # 这个列表每个元素的含义是“内层用时”，以便最后通过 `用时 - 内层用时` 得到 `自身用时`
        inner_elapsed_stack: list[float] = []

        @contextmanager
        def record(item_type: str):
            inner_elapsed_stack.append(0)
            t = time.perf_counter()
            try:
                yield
            finally:
                elapsed = time.perf_counter() - t
                inner_elapsed = inner_elapsed_stack.pop()
                item_times[item_type] += elapsed - inner_elapsed

                if inner_elapsed_stack:  # 本次为内层渲染，需要将自己的耗时告诉外层
                    inner_elapsed_stack[-1] += elapsed

        # 在函数内定义 render patch
        # 使得 render 中可以直接访问到 item_times 闭包
        @staticmethod
        def render(renders: Iterable[ItemWithRenderFunc], blending: bool) -> None:
            with record('gap'):
                for data, render in renders:
                    with record(data.__class__.__name__):
                        render(data)

                    if not blending:
                        gl.glFlush()

        orig_render = RenderCollection._render
        RenderCollection._render = render
        try:
            yield
        finally:
            RenderCollection._render = orig_render


@dataclass
class FrameRecord:
    """
    各个种类物件在单帧中的耗时统计
    """

    timestamp: float
    elapsed: float = 0.0

    # key: 物件类型名称 (e.g. "VItem")
    # value: 累计耗时(秒)
    item_times: dict[str, float] = field(default_factory=lambda: defaultdict(float))
