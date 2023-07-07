from __future__ import annotations
from typing import Iterable

import numpy as np
from functools import wraps

from janim.items.item import Item
from janim.utils.iterables import resize_with_interpolation
from janim.shaders.render import RenderData
from janim.shaders.render import DotCloudRenderer

from constants import Iterable

class DotCloud(Item):
    radius = 0.05

    def __init__(self, points: Iterable):
        super().__init__()

        # 半径数据
        self.radii = np.array([self.radius], dtype=np.float32)  # radii 在所有操作中都会保持 dtype=np.float32，以便传入 shader
        self.needs_new_radii = True

        self.set_points(points)

    def points_count_changed(self) -> None:
        super().points_count_changed()
        self.needs_new_radii = True
    
    def create_renderer(self) -> DotCloudRenderer:
        return DotCloudRenderer()
    
    def set_radius(self, radius: float | Iterable[float]):
        if not isinstance(radius, Iterable):
            radius = [radius]
        radius = resize_with_interpolation(np.array(radius), self.points_count())
        if len(radius) == len(self.radii):
            self.radii[:] = radius
        else:
            self.radii = radius.astype(np.float32)
        return self
    
    def get_radii(self) -> np.ndarray:
        if self.needs_new_radii:
            if self.has_points():
                self.set_radius(self.radii)
            else:
                self.radii = np.array([self.radius], dtype=np.float32)
            self.needs_new_radii = False
        return self.radii
    
    def get_radius(self) -> float:
        return self.get_radii().max()

    def scale(
        self,
        scale_factor: float | Iterable,
        scale_radii: bool = True,
        **kwargs
    ):
        super().scale(scale_factor, **kwargs)
        if scale_radii:
            self.set_radii(scale_factor * self.get_radii())
        return self
        
