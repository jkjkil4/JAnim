from __future__ import annotations
from typing import Callable, Optional, TypeVar

import numpy as np
from janim.constants import np
from janim.typing import Self

import copy

from janim.items.item import Item
from janim.utils.bezier import interpolate

T = TypeVar("T")

class ValueTracker(Item):
    def __init__(
        self, 
        value: T, 
        interpolate_fn: Callable[[T, T, float], T] = interpolate,
        copy_fn: Callable[[T], T] = copy.copy,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.value = value
        self.interpolate_fn = interpolate_fn
        self.copy_fn = copy_fn
    
    def get(self) -> T:
        return self.value
    
    def set(self, value: T) -> None:
        self.value = value

    def copy(self) -> Self:
        copy_item = super().copy()
        copy_item.value = self.copy_fn(self.value)
        return copy_item

    def interpolate(
        self, 
        item1: ValueTracker, 
        item2: ValueTracker, 
        alpha: float, 
        path_func: Callable[[np.ndarray, np.ndarray, float], np.ndarray], 
        npdata_to_copy_and_interpolate: Optional[list[tuple[str, str, str]]] = None
    ) -> Self:
        super().interpolate(item1, item2, alpha, path_func, npdata_to_copy_and_interpolate)
        self.value = self.interpolate_fn(item1.value, item2.value, alpha)

