
import time

from PySide6.QtCore import QTimer, QObject, Qt, Signal


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


class PreciseTimerWithFPS(PreciseTimer):
    fps_updated = Signal(int)

    def __init__(self, duration: float | None = None, parent: QObject | None = None):
        super().__init__(duration, parent)

        self.reset_fps_counter()
        self._fps = 0

    @property
    def fps(self) -> int:
        return self._fps

    @property
    def latest(self) -> float:
        return self._latest

    def reset_fps_counter(self) -> None:
        self._start = time.time()
        self._counter = 0
        self._latest = self._start

    def start_precise_timer(self) -> None:
        super().start_precise_timer()
        self.reset_fps_counter()

    def set_skip_enabled(self, enabled: bool) -> None:
        super().set_skip_enabled(enabled)
        self.reset_fps_counter()

    def on_timeout(self) -> None:
        super().on_timeout()
        self._counter += 1
        self._latest = time.time()
        if self._latest - self._start >= 1:
            self._fps = self._counter
            self.fps_updated.emit(self._fps)
            self._counter = 0
            self._start = self._latest
