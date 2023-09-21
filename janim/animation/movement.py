from __future__ import annotations
from typing import Callable, Sequence

from janim.constants import *
from janim.animation.animation import ItemAnimation
from janim.items.item import Item

class Homotopy(ItemAnimation):
    def __init__(
        self,
        homotopy: Callable[[float, float, float, float], Sequence[float]],
        item: Item,
        *,
        run_time: float = 3,
        apply_function_kwargs: dict = {},
        **kwargs
    ) -> None:
        '''
        Homotopy is a function from
        (x, y, z, t) to (x', y', z')
        '''
        self.homotopy = homotopy
        self.apply_function_kwargs = apply_function_kwargs
        super().__init__(item, run_time=run_time, **kwargs)

        self.item_copy = None

    def function_at_time_t(
        self,
        t: float
    ) -> Callable[[np.ndarray], Sequence[float]]:
        return lambda p: self.homotopy(*p, t)
    
    def create_interpolate_datas(self) -> tuple:
        if self.item_copy is None:
            self.item_copy = self.item_for_anim.copy()

        return (self.item_copy.get_family(), )
    
    def interpolate_subitem(
        self, 
        item: Item, 
        interpolate_data: tuple, 
        alpha: float
    ) -> None:
        starting_item, = interpolate_data
        item.match_points(starting_item)
        item.apply_function(
            self.function_at_time_t(alpha),
            **self.apply_function_kwargs
        )

# TODO: SmoothedVectorizedHomotopy
# TODO: ComplexHomotopy
# TODO: PhaseFlow
# TODO: MoveAlongPath

