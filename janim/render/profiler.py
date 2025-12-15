import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, Deque


@dataclass
class FrameRecord:
    """记录单帧的性能数据"""

    timestamp: float
    total_time: float = 0.0
    # key: 物件类型名称 (e.g. "VItem"), value: 累计耗时(秒)
    item_times: Dict[str, float] = field(default_factory=lambda: defaultdict(float))


class RenderProfiler:
    def __init__(self, max_history: int = 200):
        self.history: Deque[FrameRecord] = deque(maxlen=max_history)
        self.current_record: FrameRecord | None = None
        self._t_start: float = 0.0

    def start_frame(self):
        """每帧渲染开始时调用"""
        self.current_record = FrameRecord(timestamp=time.time())
        self._t_start = time.perf_counter()

    def record_item(self, item_type: str, duration: float):
        """记录单个物件的渲染耗时"""
        if self.current_record:
            self.current_record.item_times[item_type] += duration

    def end_frame(self):
        """每帧渲染结束时调用"""
        if self.current_record:
            self.current_record.total_time = time.perf_counter() - self._t_start
            self.history.append(self.current_record)

    def get_latest_stats(self) -> FrameRecord | None:
        """获取最近一帧的数据"""
        return self.history[-1] if self.history else None
