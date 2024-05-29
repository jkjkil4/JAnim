
import time

from PySide6.QtCore import QTimer, QObject, Qt


class PreciseTimer(QTimer):
    def __init__(self, duration: float | None = None, parent: QObject | None = None):
        super().__init__(parent)

        self.duration = duration

        self.setTimerType(Qt.TimerType.PreciseTimer)
        self.timeout.connect(self.on_timeout)

    def set_duration(self, duration: float) -> None:
        self.duration = duration

    def start_precise_timer(self) -> None:
        assert self.duration is not None
        self.scheduled = 0
        self.start_time = time.time()
        self.start(int(self.duration * 1000))

    def on_timeout(self) -> None:
        if not self.isActive():
            return

        self.scheduled += self.duration
        elapsed = time.time() - self.start_time

        delta = self.scheduled - elapsed

        if abs(delta) > 2 * self.duration:
            self.start_precise_timer()
            return

        self.start(max(0, int((self.duration + delta) * 1000)))
