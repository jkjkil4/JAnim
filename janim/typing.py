from typing import Iterable, Protocol, Callable, Self, runtime_checkable

import numpy as np

Vect = Iterable[float] | np.ndarray
VectArray = Iterable[Vect] | np.ndarray


@runtime_checkable
class SupportsRefreshWithRecurse(Protocol):
    def mark_refresh(self, func: Callable | str, *, recurse_up=False, recurse_down=False) -> Self: ...
