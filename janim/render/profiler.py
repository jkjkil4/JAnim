import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterable

import OpenGL.GL as gl

from janim.anims.timeline import BuiltTimeline, ItemWithRenderFunc
from janim.render.collection import RenderCollection


class RenderProfiler:
    """
    性能分析器

    用于 patch 物件渲染，统计物件渲染的耗时与性能
    """

    def __init__(self, built: BuiltTimeline, *, max_history: int = 200):
        self._built = built
        self._orig_cls = built._RenderCollectionCls
        self._WrapperCls = _make_wrapper(self)

        self.max_history = max_history
        self.history: deque[FrameRecord] = deque(maxlen=max_history)
        self.recording: FrameRecord | None = None

        self.attach()

    def set_built(self, built: BuiltTimeline):
        self.detach()
        self._built = built
        self._orig_cls = built._RenderCollectionCls
        self.attach()

    def attach(self) -> None:
        """挂载性能分析器"""
        self._built._RenderCollectionCls = self._WrapperCls

    def detach(self) -> None:
        """卸载性能分析器"""
        self._built._RenderCollectionCls = self._orig_cls

    @contextmanager
    def records(self):
        """
        使用 ``with`` 语句包裹每帧渲染，收集其中所有的 ``record_item`` 统计数据
        """
        is_nested = self.recording is not None
        if not is_nested:
            self.recording = FrameRecord(timestamp=time.time())
        t_start = time.perf_counter()
        try:
            yield
        finally:
            self.recording.total_time = time.perf_counter() - t_start
            self.history.append(self.recording)
            if not is_nested:
                self.recording = None

    def record_item(self, item_type: str, duration: float):
        """
        记录单个物件的渲染耗时
        """
        assert self.recording is not None
        self.recording.item_times[item_type] += duration


@dataclass
class FrameRecord:
    """
    各个种类物件在单帧中的耗时统计
    """

    timestamp: float
    total_time: float = 0.0

    # key: 物件类型名称 (e.g. "VItem")
    # value: 累计耗时(秒)
    item_times: dict[str, float] = field(default_factory=lambda: defaultdict(float))


def _make_wrapper(profiler: RenderProfiler):
    class _RenderCollectionWrapper(RenderCollection):
        @classmethod
        def _render(cls, renders: Iterable[ItemWithRenderFunc], blending: bool) -> None:
            with profiler.records():
                for data, render in renders:
                    t0 = time.perf_counter()
                    render(data)
                    dt = time.perf_counter() - t0
                    item_type = data.__class__.__name__
                    profiler.record_item(item_type, dt)

                    # 如果没有 blending，我们认为当前是在向透明 framebuffer 绘制
                    # 所以每次都需要使用 glFlush 更新 framebuffer 信息使得正确渲染
                    if not blending:
                        gl.glFlush()

    return _RenderCollectionWrapper
