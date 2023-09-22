
from janim.constants import *
from janim.animation.animation import Animation
from janim.items.item import Item
from janim.utils.rate_functions import RateFunc, linear, smooth

class Rotating(Animation):
    def __init__(
        self,
        item: Item,
        angle: float = TAU,
        axis: np.ndarray = OUT,
        *,
        run_time: float = 5,
        rate_func: RateFunc = linear,
        about_point: np.ndarray | None = None,
        about_edge: np.ndarray | None = None,
        # TODO: suspend_item_updating: bool = False,
        **kwargs
    ) -> None:
        self.item_for_anim = item
        self.angle = angle
        self.axis = axis
        self.about_point = about_point
        self.about_edge = about_edge
        super().__init__(run_time=run_time, rate_func=rate_func, **kwargs)

        self.item_copy = None

    def begin(self) -> None:
        self.make_visible(self.item_for_anim)

        if self.item_copy is None:
            self.item_copy = self.item_for_anim.copy()
    
    def interpolate(self, alpha) -> None:
        for item1, item2 in zip(self.item_for_anim.get_family(), self.item_copy.get_family()):
            item1.set_points(item2.get_points())
        self.item_for_anim.rotate(
            alpha * self.angle,
            axis=self.axis,
            about_point=self.about_point,
            about_edge=self.about_edge
        )

class Rotate(Rotating):
    def __init__(
        self,
        item: Item,
        angle: float = PI,
        *,
        run_time: float = 1,
        rate_func: RateFunc = smooth,
        about_edge: np.ndarray = ORIGIN,
        **kwargs
    ) -> None:
        super().__init__(
            item, 
            angle, 
            run_time=run_time, 
            rate_func=rate_func, 
            about_edge=about_edge,
            **kwargs
        )
