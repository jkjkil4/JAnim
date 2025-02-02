from __future__ import annotations

from janim.anims.animation import TimeAligner
from janim.items.item import Item


class AnimStack:
    '''
    用于在 :class:`~.Timeline` 中记录作用于 :class:`~.Item` 上的 :class:`~.Animation`

    可使用 :meth:`to_executor` 得到 :class:`AnimExecutor`
    '''
    def __init__(self, time_aligner: TimeAligner):
        self.time_aligner = time_aligner

    def detect_change(self, item: Item, at: float) -> None:
        pass

    def to_executor(self) -> AnimExecutor:
        pass


class AnimExecutor:
    pass
