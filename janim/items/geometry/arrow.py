from __future__ import annotations

import numpy as np
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
    '''
    箭头标志

    - `body_length`: 箭头的宽度
    - `back_width`: 箭头的长度
    - `center_anchor`: 原点所处的位置，请参考 `ArrowTip.CenterAnchor`
    '''

    class CenterAnchor(Enum):
        '''
        原点所处位置的选项
        
        图形示意：
        ```txt
          .-----
          |        -----
          |               -----
        [Back]  [Center]  [Front]
          |               -----
          |        -----
          .-----
        ```
        '''
        Back = 0
        Center = 1
        Front = 2

    def __init__(   # TODO: 3d-ops
        self,
        body_length: float = DEFAULT_ARROWTIP_BODY_LENGTH,
        back_width: float = DEFAULT_ARROWTIP_BACK_WIDTH,
        angle: float = 0,
        *,
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
        '''
        根据设定的 `center_anchor`得到原点位置，
        请参考 `ArrowTip.CenterAnchor`
        '''
        if self.center_anchor == ArrowTip.CenterAnchor.Back:
            return self.points[4]
        if self.center_anchor == ArrowTip.CenterAnchor.Center:
            return midpoint(self.points[0], self.points[4])
        # if self.center_anchor == ArrowTip.CenterAnchor.Front:
        return self.points[0]

    def get_direction(self) -> np.ndarray:
        '''得到箭头的方向（单位向量）'''
        return normalize(self.points[0] - self.points[4])
    
    def get_body_length(self) -> float:
        '''得到箭头的长度'''
        return get_norm(self.points[0] - self.points[4])
    
    def get_back_width(self) -> float:
        '''得到箭头的宽度'''
        return get_norm(self.points[5] - self.points[3])
    
    def rotate_about_anchor(self, angle: float) -> Self:
        '''相对于原点位置进行旋转'''
        self.rotate(angle, about_point=self.get_center_anchor())
        return self
    
    def move_anchor_to(self, pos: np.ndarray) -> Self:
        '''将原点移动到指定位置'''
        self.shift(pos - self.get_center_anchor())
        return self
    
class Arrow(Line):
    '''
    带箭头的线段，箭头大小自动

    - `buff`: 箭头首尾的空余量，默认为 0.25
    - `max_length_to_tip_length_ratio`: 箭头长度和直线长度最大比例
    '''
    def __init__(
        self,
        start: np.ndarray = LEFT,
        end: np.ndarray = RIGHT,
        *,
        buff: float = 0.25,
        max_length_to_tip_length_ratio: float | None = 0.3,
        tip_kwargs: dict = {},
        **kwargs
    ) -> None:
        super().__init__(start, end, buff=buff, **kwargs)
        self.max_length_to_tip_length_ratio = max_length_to_tip_length_ratio
        
        self.init_tips(tip_kwargs)
        self.place_tip()

    def init_tips(self, tip_kwargs: dict) -> None:
        self.tip = self.add_tip(**tip_kwargs)
        self.tip_orig_body_length = self.tip.get_body_length()
    
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
    
    def _place_tip(
        self, 
        tip: ArrowTip, 
        target: np.ndarray, 
        target_direction: np.ndarray
    ) -> None:
        direction = tip.get_direction()

        length = self.tip_orig_body_length

        if self.max_length_to_tip_length_ratio:
            max_length = self.get_arc_length() * self.max_length_to_tip_length_ratio
            length = min(length, max_length)

        min_length = self.get_stroke_width()[0] * self.tip.get_body_length() / self.tip.get_back_width()
        length = max(length, min_length)

        scale_factor = length / tip.get_body_length()

        tip.scale(scale_factor)
        if not np.isclose(direction, target_direction).all():
            tip.apply_matrix(rotation_between_vectors(direction, target_direction))
        tip.move_anchor_to(target)

    def place_tip(self) -> Self:
        self._place_tip(self.tip, self.points[-1], self.get_end_direction())        
        return self

class Vector(Arrow):
    '''
    起点为 ORIGIN 的箭头，终点为 `direction`

    - `buff` 默认设为了 0
    '''
    def __init__(self, direction: np.ndarray = RIGHT, *, buff: float = 0, **kwargs):
        if len(direction) == 2:
            direction = np.hstack([direction, 0])
        super().__init__(ORIGIN, direction, buff=buff, **kwargs)

class DoubleArrow(Arrow):
    '''
    双向箭头

    参数请参考 `Arrow`
    '''
    def __init__(self, *args, tip_kwargs: dict = {}, **kwargs) -> None:
        super().__init__(*args, tip_kwargs=tip_kwargs, **kwargs)
    
    def init_tips(self, tip_kwargs: dict) -> None:
        super().init_tips(tip_kwargs)
        self.start_tip = self.add_tip(0, True, **tip_kwargs)
    
    def copy(self) -> Self:
        copy_item = super().copy()
        copy_item.start_tip = copy_item[1]
        return copy_item

    def place_tip(self) -> Self:
        super().place_tip()
        self._place_tip(self.start_tip, self.points[0], -self.get_start_direction())
        return self

# TODO: FillArrow
