from __future__ import annotations

from janim.anims.animation import Animation, TimeAligner
from janim.anims.display import Display
from janim.constants import FOREVER
from janim.items.item import Item


class AnimStack:
    '''
    用于在 :class:`~.Timeline` 中记录作用于 :class:`~.Item` 上的 :class:`~.Animation`

    可使用 :meth:`to_executor` 得到 :class:`AnimExecutor`
    '''
    def __init__(self, time_aligner: TimeAligner):
        self.time_aligner = time_aligner

        # 在跟踪物件变化时，该变量用于对比物件与先前记录的 Display 对象进行对比
        # 如果发生变化，则记录新的 Display 对象
        self.prev_display: Display | None = None

        self.stack: list[Animation] = []

    def detect_change(self, item: Item, at: float) -> None:
        if self.prev_display is None or not self.prev_display.data.not_changed(item):
            anim = Display(item, item.store(), at=at, duration=FOREVER)
            self.time_aligner.align(anim)
            self.prev_display = anim
            # _time_fixed 会产生对 self.append 的调用，因此不用再另外 self.append
            anim._time_fixed()

    def append(self, anim: Animation) -> None:
        self.stack.append(anim)

    def to_executor(self) -> AnimExecutor:
        pass


class AnimExecutor:
    pass
