from typing import Callable

from enum import Enum

from janim.constants import *
from janim.utils.rate_functions import smooth

class Animation:
    '''
    动画基类
    - 创建一个从 `begin_time` 持续至 `begin_time + run_time` 的动画
    - 指定 `rate_func` 可以设定插值函数，默认为 `smooth` 即平滑插值
    - 实现了对 `begin`、`interpolate` 和 `finish` 的封装，子类进行功能实现
    '''
    class _State(Enum):
        '''
        标记当前动画的执行状态
        '''
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
        '''
        根据 `elapsed` 已过时间，得到其从 `begin_time` 至 `begin_time + run_time` 的占比
        '''
        return (elapsed - self.begin_time) / self.run_time

    def update(self, elapsed, dt) -> None:
        '''
        根据 `elapsed` 已过时间，更新动画状态并进行处理

        - 当 `elapsed` 达到 `begin_time`，则会调用 `begin` 且进入 `OnExec` 状态，在该状态中会持续调用 `interpolate` 进行动画插值；
        - 当 `elapsed` 继续前进，达到 `begin_time + run_time`，则会调用 `finish` 且进入 `AfterExec` 状态，结束当前动画的处理。
        '''
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
        '''
        在该方法中编写用于初始化动画执行的代码，
        由子类实现具体功能
        '''
        pass

    def interpolate(self, alpha) -> None:
        '''
        在该方法中编写用于插值动画的代码，
        由子类实现具体功能
        '''
        pass

    def finish(self) -> None:
        '''
        在该方法中编写用于结束动画执行的代码，
        由子类实现具体功能
        '''
        pass

    def finish_all(self) -> None:
        '''
        用于整个动画执行的扫尾，以保证达到 `AfterExec` 状态
        '''
        if self.state == self._State.BeforeExec:
            self.begin()
            self.state = self._State.OnExec

        if self.state == self._State.OnExec:
            self.finish()
            self.state = self._State.AfterExec