
from janim.constants import *
from janim.items.item import Item
from janim.animation.transform import Transform


class Fade(Transform):
    def __init__(
        self,
        item: Item,
        shift: np.ndarray = ORIGIN,
        scale: float = 1.0,
        **kwargs
    ) -> None:
        self.shift_vect = shift
        self.scale_factor = scale
        super().__init__(item, item, **kwargs)

class FadeIn(Fade):
    def begin(self) -> None:
        self.item_copy = self.item.copy().set_opacity(0)
        if np.any(self.shift_vect != ORIGIN):
            self.item_copy.shift(-self.shift_vect)
        if self.scale_factor != 1.0:
            self.item_copy.scale(1 / self.scale_factor)
        super().begin()

class FadeOut(Fade):
    def begin(self) -> None:
        self.target_copy = self.target_item.copy().set_opacity(0)
        if np.any(self.shift_vect != ORIGIN):
            self.target_copy.shift(self.shift_vect)
        if self.scale_factor != 1.0:
            self.target_copy.scale(self.scale_factor)
        super().begin()
    
    def finish(self) -> None:
        super().finish()
        self.item_for_anim.become(self.item_copy)
        self.item_for_anim.set_visible(False)
