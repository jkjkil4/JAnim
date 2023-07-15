
from janim.constants import *
from janim.items.item import Item
from janim.utils.space_ops import get_norm

from janim.shaders.texture import Texture
from janim.shaders.render import ImgItemRenderer

class ImgItem(Item):
    def __init__(
        self,
        filepath: str,
        height: float = 4,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.texture = Texture.get(filepath)
        self.set_points([UR, DR, DL, UL])

        self.set_size(height * self.texture.img.width() / self.texture.img.height(), height)
    
    def create_renderer(self) -> ImgItemRenderer:
        return ImgItemRenderer()
    
    def get_horizontal_vect(self) -> np.ndarray:
        return self.points[1] - self.points[2]

    def get_horizontal_dist(self) -> float:
        return get_norm(self.get_horizontal_vect())
    
    def get_vertical_vect(self) -> np.ndarray:
        return self.points[3] - self.points[2]
    
    def get_vertical_dist(self) -> float:
        return get_norm(self.get_vertical_vect())
    
    # TODO: point_to_rgba
