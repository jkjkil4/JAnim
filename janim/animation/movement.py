from __future__ import annotations
from typing import Callable, Sequence

from janim.constants import *
from janim.animation.animation import SelfAnimation
from janim.items.item import Item

class Homotopy(SelfAnimation):
    '''
    homotopy 是一个从 (x, y, z, t) 到 (x’, y’, z’) 的函数。
    t 的取值范围是 [0, 1]， 让 mobject 根据 homotopy 计算的每个点坐标进行变换。
    
    例子中 t = 0 时 mob 是边长为 0 的正方形， t = 1 时是边长为 2 的正方形。
    
    与 Transform 类似，区别在于 Transform 锚点运动轨迹是直线，
    Homotopy 锚点运动轨迹是根据传入的 homotopy 计算的。
    '''
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

    def function_at_time_t(
        self,
        t: float
    ) -> Callable[[np.ndarray], Sequence[float]]:
        return lambda p: self.homotopy(*p, t)
    
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

