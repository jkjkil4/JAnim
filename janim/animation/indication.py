from __future__ import annotations

from janim.constants import *
from janim.items.item import Item
from janim.items.geometry.arc import Dot
from janim.animation.transform import Transform

class FocusOn(Transform):
    def __init__(
        self, 
        focus_point: np.ndarray | Item, 
        opacity: float = 0.2,
        color: JAnimColor = GREY,
        run_time: float = 2,
        **kwargs
    ):
        self.focus_point = focus_point

        self.start_dot = Dot(
            radius=FRAME_X_RADIUS + FRAME_Y_RADIUS,
            fill_color=color,
            fill_opacity=0,
        )

        self.target_dot = Dot(radius=0)
        self.target_dot.set_fill(color, opacity)
        self.target_dot.add_updater(lambda d: d.move_to(self.focus_point))

        super().__init__(self.start_dot, self.target_dot, run_time=run_time, **kwargs)

    def update(self, elapsed, dt) -> None:
        super().update(elapsed, dt)
        self.target_dot.update(dt)

    def begin(self) -> None:
        self.target_copy = self.target_dot
        super().begin()
    
    def finish(self) -> None:
        super().finish()
        self.scene.remove(self.start_dot)


