from __future__ import annotations
from typing import Iterable
from janim.typing import Self

import numpy as np

from janim.items.item import Item
from janim.utils.iterables import resize_array
from janim.constants import *

class DotCloud(Item):
    def __init__(
        self, 
        points: Iterable,
        color: JAnimColor = GREY_C,
        radius: float = 0.05,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.radius = radius

        # 半径数据
        self.radii = np.array([self.radius], dtype=np.float32)  # radii 在所有操作中都会保持 dtype=np.float32，以便传入 shader

        self.npdata_to_copy_and_interpolate.update((
            ('radii', 'get_radii', 'set_radius'),
        ))

        self.set_points(points)
        self.set_points_color(color)

    def points_count_changed(self) -> None:
        super().points_count_changed()
        self.mark_flag(self.get_radii)

    def radii_changed(self) -> None:
        self.mark_flag(self.get_radii, 'render')
    
    def create_renderer(self):
        from janim.gl.render import DotCloudRenderer
        return DotCloudRenderer()
    
    def set_radius(self, radius: float | Iterable[float]) -> Self:
        if not isinstance(radius, Iterable):
            radius = [radius]
        radius = resize_array(
            np.array(radius, dtype=np.float32), 
            max(1, self.points_count())
        )
        if len(radius) == len(self.radii):
            self.radii[:] = radius
        else:
            self.radii = radius
        self.radii_changed()
        return self
    
    def get_radii(self) -> np.ndarray:
        if self.take_self_flag():
            self.set_radius(self.radii)
        return self.radii
    
    def get_radius(self) -> float:
        return self.get_radii().max()
    
    def compute_bbox(self) -> np.ndarray:
        bb = super().compute_bbox()
        radius = self.get_radius()
        bb[0] += np.full((3,), -radius)
        bb[2] += np.full((3,), radius)
        return bb

    def scale(
        self,
        scale_factor: float | Iterable,
        scale_radii: bool = True,
        **kwargs
    ) -> Self:
        super().scale(scale_factor, **kwargs)
        if scale_radii:
            self.set_radius(scale_factor * self.get_radii())
        return self
    
    def reverse_points(self, recurse=True) -> Self:
        super().reverse_points(recurse)
        self.set_radius(self.get_radii()[::-1])
        return self
