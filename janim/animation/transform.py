
from typing import Callable, Optional

from janim.constants import *
from janim.animation.animation import Animation
from janim.items.item import Item
from janim.utils.paths import straight_path, path_along_arc

class Transform(Animation):
    def __init__(
        self,
        item: Item,
        target_item: Item,
        path_arc: float = 0,
        path_arc_axis: np.ndarray = OUT,
        path_func: Optional[Callable] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.item = item
        self.target_item = target_item

        self.path_func = path_func or self.create_path_func(path_arc, path_arc_axis)

    @staticmethod
    def create_path_func(
        path_arc: float,
        path_arc_axis: np.ndarray
    ) -> Callable[[np.ndarray, np.ndarray, float], np.ndarray]:
        if path_arc == 0:
            return straight_path
        return path_along_arc(
            path_arc,
            path_arc_axis
        )

    def begin(self) -> None:
        self.target_copy = self.target_item.copy()
        