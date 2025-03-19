from __future__ import annotations

from typing import Self

from janim.components.component import Component


class Cmpt_List[ItemT, T](list[T], Component[ItemT]):
    def copy(self) -> Self:
        return Component.copy(self)

    def become(self, other: Cmpt_List) -> Self:
        self.clear()
        self.extend(other)
        return self

    def not_changed(self, other: Cmpt_List) -> Self:
        return len(self) == len(other) and all(a == b for a, b in zip(self, other))
