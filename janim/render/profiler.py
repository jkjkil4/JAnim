from __future__ import annotations

import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from janim.anims.timeline import ItemWithRenderFunc
from janim.render.collection import RenderCollection


class RenderProfiler:
    """
    性能分析器

    用于 patch 物件渲染，统计物件渲染的耗时与性能

    :param callback: 用于接收结果的回调函数，接收一个 :class:`FrameRecord` 参数
    """

    def __init__(self, callback: Callable[[FrameRecord], Any]):
        self._callback = callback

    @contextmanager
    def record_frame(self):
        """
        在渲染顶层入口 ``with`` 该函数，统计内部代码块的物件用时，并将结果传递给 ``callback`` 回调
        """
        t = time.perf_counter()
        item_times: dict[str, float] = defaultdict(float)
        try:
            with self._patch_collection_render(item_times):
                yield
        finally:
            elapsed = time.perf_counter() - t
            times = list(item_times.items())
            times.sort(key=lambda x: x[0])
            self._callback(FrameRecord(t, elapsed, times))

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
        def render(renders: Iterable[ItemWithRenderFunc]) -> None:
            with record('gap'):
                for data, render in renders:
                    with record(data.__class__.__name__):
                        render(data)

        orig_render = RenderCollection.__dict__['_render']
        RenderCollection._render = render
        try:
            yield
        finally:
            setattr(RenderCollection, '_render', orig_render)


@dataclass
class FrameRecord:
    """
    各个种类物件在单帧中的耗时统计
    """

    timestamp: float
    elapsed: float

    # tuple[str, float]:
    #   物件类型名称 (e.g. "VItem")
    #   累计耗时(秒)
    #
    # 列表元素按照 str 排序
    times: list[tuple[str, float]]

    def __post_init__(self):
        # 和 elapsed 的区别：
        # elapsed 会包括完整的 overhead，total_time 是内部用时求和，不包含 overhead
        self.total_time = sum(t for _, t in self.times)
