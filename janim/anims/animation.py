from abc import ABCMeta
from dataclasses import dataclass

from janim.utils.rate_functions import RateFunc, smooth


@dataclass
class TimeRange:
    at: float
    duration: float

    @property
    def end(self) -> float:
        return self.at + self.duration


class Animation(metaclass=ABCMeta):
    def __init__(
        self,
        *,
        at: float = 0,
        duration: float = 1.0,
        rate_func: RateFunc = smooth
    ):
        from janim.anims.timeline import Timeline
        self.timeline = Timeline.get_context()

        self.local_range = TimeRange(at, duration)
        self.global_range = None
        self.rate_func = rate_func

    def set_global_range(self, at: float, duration: float | None = None) -> None:
        if duration is None:
            duration = self.local_range.duration
        self.global_range = TimeRange(at, duration)

    def anim_init(self) -> None: ...

    def anim_on(self, local_t: float) -> None:
        alpha = self.rate_func(local_t / self.local_range.duration)
        self.anim_on_alpha(alpha)

    def anim_on_alpha(self, alpha: float) -> None:
        pass
