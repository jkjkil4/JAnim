from __future__ import annotations
from typing import Optional, Callable

import numpy as np
import traceback

from PySide6.QtCore import Qt, QObject, QTimer, QEventLoop

class LoopHelper(QObject):
    def __init__(
        self, 
        frame_rate: float, 
        parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)
        self.frame_rate = frame_rate

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.event_loop = QEventLoop(self)
    
    def exec(self, fn_progress: Callable[[float]], duration: float) -> None:
        dt_ms = 1000 / self.frame_rate
        dt = dt_ms / 1000
        times = np.ceil(duration * self.frame_rate)
        idx = 0
        def slot() -> None:
            nonlocal idx
            try:
                fn_progress(dt)
            except:
                traceback.print_exc()
                exit(1)
            
            idx += 1
            if idx >= times:
                self.event_loop.quit()

        connection = self.timer.timeout.connect(slot)
        self.timer.start(dt_ms)

        self.event_loop.exec()

        self.timer.disconnect(connection)
        self.timer.stop()
