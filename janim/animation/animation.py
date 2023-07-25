from typing import Callable

from enum import Enum

from janim.constants import *
from janim.utils.rate_functions import smooth

class Animation:
    class _State(Enum):
        BeforeExec = 0
        OnExec = 1
        AfterExec = 2

    def __init__(
        self,
        begin_time: float = 0.0,
        run_time: float = DEFAULT_RUN_TIME,
        rate_func: Callable[[float], float] = smooth
    ) -> None:
        self.begin_time = begin_time
        self.run_time = run_time
        self.rate_func = rate_func

        self.state = Animation._State.BeforeExec

    def get_alpha(self, elapsed: float) -> float:
        return (elapsed - self.begin_time) / self.run_time

    def update(self, elapsed, dt) -> None:
        # 使用 < 判断处于前一状态，使用 >= 判断进入后一状态

        # 检查并切换状态
        if self.state == self._State.BeforeExec and elapsed >= self.begin_time:
            self.begin()
            self.state = self._State.OnExec
        
        if self.state == self._State.OnExec and elapsed >= self.begin_time + self.run_time:
            self.finish()
            self.state = self._State.AfterExec

        # 常规处理
        if self.state == self._State.OnExec:
            self.interpolate(self.rate_func(self.get_alpha(elapsed)))
        
    def begin(self) -> None:
        pass

    def interpolate(self, alpha) -> None:
        pass

    def finish(self) -> None:
        pass

    def finish_all(self) -> None:
        if self.state == self._State.BeforeExec:
            self.begin()
            self.state = self._State.OnExec

        if self.state == self._State.OnExec:
            self.finish()
            self.state = self._State.AfterExec