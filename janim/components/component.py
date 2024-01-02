
from typing import Callable

import janim.utils.refresh as refresh
from janim.typing import Self


class Component(refresh.Refreshable):
    def mark_refresh(self, func: Callable | str, *, recurse_up: bool = False, recurse_down: bool = False) -> Self:
        super().mark_refresh(func)

        # from janim.items.item import ItemBase


