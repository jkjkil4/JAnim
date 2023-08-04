from __future__ import annotations
from janim.constants import np
from janim.typing import Self

from enum import Enum
import math

from janim.constants import *
from janim.items.vitem import VItem, DEFAULT_STROKE_WIDTH
from janim.items.geometry.line import Line
from janim.utils.space_ops import midpoint, get_norm, normalize, rotation_between_vectors

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

    def get_direction(self) -> np.ndarray:
        return normalize(self.points[0] - self.points[4])
    
    def get_body_length(self) -> float:
        return get_norm(self.points[0] - self.points[4])
    
    def get_back_width(self) -> float:
        return get_norm(self.points[5] - self.points[3])
    
    def rotate_about_anchor(self, angle: float) -> Self:
        self.rotate(angle, about_point=self.get_center_anchor())
        return self
    
    def move_anchor_to(self, pos: np.ndarray) -> Self:
        self.shift(pos - self.get_center_anchor())
        return self
    
class Arrow(Line):
    def __init__(
        self,
        start: np.ndarray = LEFT,
        end: np.ndarray = RIGHT,
        buff: float = 0.25,
        max_length_to_tip_length_ratio: float = 0.3,
        tip_kwargs: dict = {},
        **kwargs
    ) -> None:
        super().__init__(start, end, buff=buff, **kwargs)
        self.max_length_to_tip_length_ratio = max_length_to_tip_length_ratio
        
        self.tip = self.add_tip(**tip_kwargs)
        self.tip_orig_body_length = self.tip.get_body_length()
        
        self.place_tip()

    def copy(self) -> Self:
        copy_item = super().copy()
        copy_item.tip = copy_item.items[0]
        return copy_item

    def get_direction(self) -> np.ndarray:
        return normalize(self.points[-1] - self.points[-2])
    
    def get_arc_length(self) -> float:
        # Push up into Line?
        arc_len = get_norm(self.get_vector())
        if self.path_arc > 0:
            arc_len *= self.path_arc / (2 * math.sin(self.path_arc / 2))
        return arc_len
    
    def place_tip(self) -> Self:
        direction = self.tip.get_direction()
        target_direction = self.get_direction()
        max_length = self.get_arc_length() * self.max_length_to_tip_length_ratio
        length = min(self.tip_orig_body_length, max_length)
        scale_factor = length / self.tip.get_body_length()

        self.tip.scale(scale_factor)
        if not np.isclose(direction, target_direction).all():
            self.tip.apply_matrix(rotation_between_vectors(direction, target_direction),)
        self.tip.move_anchor_to(self.points[-1])
        
        return self



# TODO: Arrow
# TODO: FillArrow
# TODO: Vector
# TODO: DoubleArrow

# TODO: CurvedArrow
# TODO: CurvedDoubleArrow

