from typing import Iterable

from janim.items.item import Item
from janim.shaders.render import RenderData

from shaders.render import DotCloudRenderer

class DotCloud(Item):
    def __init__(self, points: Iterable):
        super().__init__()
        self.set_points(points)
    
    def create_renderer(self) -> DotCloudRenderer:
        return DotCloudRenderer()
        
