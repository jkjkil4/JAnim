from __future__ import annotations
from janim.typing import Self

from enum import Enum

from janim.constants import *
from janim.items.vitem import VItem, DEFAULT_STROKE_WIDTH
from janim.utils.space_ops import midpoint

DEFAULT_ARROWTIP_BODY_LENGTH = 0.2
DEFAULT_ARROWTIP_BACK_WIDTH = 0.2

class ArrowTip(VItem):
    class CenterAnchor(Enum):
        Back = 0
        Center = 1
        Front = 2

    def __init__(   # TODO: 3d-ops
        self,
        body_length: float = DEFAULT_ARROWTIP_BODY_LENGTH,
        back_width: float = DEFAULT_ARROWTIP_BACK_WIDTH,
        angle: float = 0,
        center_anchor: CenterAnchor = CenterAnchor.Back,
        fill_opacity: float = 1.0,
        stroke_width: float = DEFAULT_STROKE_WIDTH / 4,
        **kwargs
    ) -> None:
        super().__init__(fill_opacity=fill_opacity, stroke_width=stroke_width, **kwargs)
        self.center_anchor = center_anchor

        self.set_points_as_corners([
            body_length * RIGHT,
            back_width / 2 * UP,
            back_width / 2 * DOWN,
            body_length * RIGHT
        ])
        self.to_center().rotate_about_anchor(angle)
    
    def get_center_anchor(self) -> np.ndarray:
        if self.center_anchor == ArrowTip.CenterAnchor.Back:
            return self.points[4]
        if self.center_anchor == ArrowTip.CenterAnchor.Center:
            return midpoint(self.points[0], self.points[4])
        # if self.center_anchor == ArrowTip.CenterAnchor.Front:
        return self.points[0]
    
    def rotate_about_anchor(self, angle: float) -> Self:
        self.rotate(angle, about_point=self.get_center_anchor())
        return self
    
    def move_anchor_to(self, pos: np.ndarray) -> Self:
        self.shift(pos - self.get_center_anchor())
        return self

# TODO: Arrow
# TODO: FillArrow
# TODO: Vector
# TODO: DoubleArrow

# TODO: CurvedArrow
# TODO: CurvedDoubleArrow

