from __future__ import annotations
from typing import Iterable, Optional
import numpy as np

from janim.items.item import Item
from janim.utils.iterables import resize_with_interpolation
from janim.shaders.render import VItemRenderer

from janim.items.item import Item

class VItem(Item):
    tolerance_for_point_equality = 1e-8

    def __init__(
        self,
        fill_color: Optional[JAnimColor] = None,
        fill_opacity = 0.0,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.fill_color = fill_color
        self.fill_opacity = fill_opacity

        # 轮廓线粗细
        self.stroke_width = np.zeros((0, 2), dtype=np.float32)  # stroke_width 在所有操作中都会保持 dtype=np.float32，以便传入 shader
        self.needs_new_stroke_width = True

        # TODO: triangulation
        pass

    def points_changed(self) -> None:
        super().points_changed()
        self.needs_new_stroke_width = True
    
    def create_renderer(self) -> VItemRenderer:
        return VItemRenderer()
    
    def set_stroke_width(self, stroke_width: float | Iterable[float]):
        if not isinstance(stroke_width, Iterable):
            stroke_width = [stroke_width]
        stroke_width = resize_with_interpolation(np.array(stroke_width), self.points_count() // 3 * 2)
        if len(stroke_width) == self.stroke_width:
            self.stroke_width[:] = stroke_width
        else:
            self.stroke_width = stroke_width.astype(np.float32)
