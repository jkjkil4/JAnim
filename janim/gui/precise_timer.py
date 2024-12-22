
import time

from PySide6.QtCore import QTimer, QObject, Qt


class PreciseTimer(QTimer):
    def __init__(self, duration: float | None = None, parent: QObject | None = None):
        super().__init__(parent)

        self.duration = duration

        self.skip_enabled = False
        self.skip_count = 0

        self.setTimerType(Qt.TimerType.PreciseTimer)
        self.timeout.connect(self.on_timeout)

    def set_duration(self, duration: float) -> None:
        self.duration = duration

    def set_skip_enabled(self, enabled: bool) -> None:
        self.skip_enabled = enabled

    def take_skip_count(self) -> int:
        count = self.skip_count
        self.skip_count = 0
        return count

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
        seconds = self.duration + delta

        if self.skip_enabled:
            while seconds < 0:
                self.scheduled += self.duration
                seconds += self.duration
                self.skip_count += 1

        else:
            if abs(delta) > 2 * self.duration:
                self.start_precise_timer()
                return

        self.start(max(0, int(seconds * 1000)))
