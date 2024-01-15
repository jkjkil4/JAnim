from __future__ import annotations

from abc import ABCMeta, abstractmethod
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from janim.items.item import Item


class Timeline(metaclass=ABCMeta):
    ctx_var: ContextVar[Timeline] = ContextVar('Timeline.ctx_var', default=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_time = 0
        # self.item_datas: dict[] = {}

    @abstractmethod
    def build(self) -> None: ...

    def _build(self) -> None:
        token = self.ctx_var.set(self)
        try:
            self.build()
        finally:
            self.ctx_var.reset(token)

    def forward(self, dt: float) -> None:
        self.current_time += dt

    def show(self, item: Item) -> None:
        pass
