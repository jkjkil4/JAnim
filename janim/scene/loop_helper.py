from __future__ import annotations
from typing import Callable

import numpy as np
import traceback
from tqdm import tqdm as ProgressDisplay

from PySide6.QtCore import Qt, QObject, QTimer, QEventLoop

class LoopHelper(QObject):
    def __init__(
        self, 
        frame_rate: float, 
        parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self.frame_rate = frame_rate

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.event_loop = QEventLoop(self)
    
    def exec(
        self, 
        fn_progress: Callable[[float]], 
        duration: float,
        delay: bool = True, 
        desc: str = ''
    ) -> bool:
        dt_ms = 1000 / self.frame_rate
        dt = dt_ms / 1000

        progress = ProgressDisplay(
            np.arange(0, duration, dt),
            leave=False,
            desc=desc
        )
        progress_iter = iter(progress)
        succ = True

        def slot() -> None:
            nonlocal succ
            try:
                fn_progress(dt)
            except:
                traceback.print_exc()
                succ = False
                self.event_loop.quit()
            
            try:
                next(progress_iter)
            except StopIteration:
                self.event_loop.quit()

        connection = self.timer.timeout.connect(slot)
        self.timer.start(dt_ms if delay else 0)

        self.event_loop.exec()

        progress.close()

        self.timer.disconnect(connection)
        self.timer.stop()

        return succ
