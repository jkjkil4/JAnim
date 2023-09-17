from __future__ import annotations
from janim.typing import Self

import math

from PySide6.QtGui import QImage
from PySide6.QtOpenGL import QOpenGLTexture

from janim.constants import *
from janim.items.item import Item
from janim.utils.simple_functions import clip
from janim.utils.space_ops import get_norm, cross, det, z_to_vector

from janim.gl.texture import Texture

class ImgItem(Item):
    min_mag_filter = QOpenGLTexture.Filter.Linear

    def __init__(
        self,
        filepath_or_img: str | QImage,
        *,
        height: float = None,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.texture = (
            Texture(filepath_or_img, self.min_mag_filter)
            if isinstance(filepath_or_img, QImage) else
            Texture.get(filepath_or_img, self.min_mag_filter)
        )
        self.set_points([UR, DR, DL, UL])

        if height is None:
            self.set_size(self.texture.img.width() * PIXEL_TO_FRAME_RATIO, self.texture.img.height() * PIXEL_TO_FRAME_RATIO)
        else:
            self.set_size(height * self.texture.img.width() / self.texture.img.height(), height)
    
    def create_renderer(self):
        from janim.gl.render import ImgItemRenderer
        return ImgItemRenderer()
    
    def get_orig(self) -> np.ndarray:
        return self.points[3]
    
    def get_horizontal_vect(self) -> np.ndarray:
        return self.points[0] - self.points[3]

    def get_horizontal_dist(self) -> float:
        return get_norm(self.get_horizontal_vect())
    
    def get_vertical_vect(self) -> np.ndarray:
        return self.points[2] - self.points[3]
    
    def get_vertical_dist(self) -> float:
        return get_norm(self.get_vertical_vect())
    
    def point_to_rgba(self, point: np.ndarray, clamp_to_edge: bool = False) -> np.ndarray:
        '''
        通过空间坐标获得对应的像素颜色
        '''
        assert(isinstance(self.texture, Texture))

        hor = self.get_horizontal_vect()
        ver = self.get_vertical_vect()
        vert = point - self.get_orig()
        normal = cross(hor, ver)

        if not np.isclose(normal, OUT).all():
            hor, ver, vert = np.dot((hor, ver, vert), z_to_vector(normal))

        u = det(vert, ver) / det(hor, ver)
        v = det(vert, hor) / det(ver, hor)
        width, height = self.texture.img.size().toTuple()
        x = math.floor(u * width)
        y = math.floor(v * height)

        if not clamp_to_edge:
            if x < 0 or x >= width or y < 0 or y >= height:
                return np.zeros(4)

        return np.array(
            self.texture.img.pixelColor(
                clip(x, 0, width - 1),
                clip(y, 0, height - 1)
            ).toTuple()
        ) / 255

    def pixel_to_point(self, x: float, y: float) -> np.ndarray:
        '''
        通过像素坐标获得对应的空间坐标，可以传入浮点值

        - 例如 `.pixel_to_point(0, 0)` 会返回原点位置（图片的左上角）
        - 例如 `.pixel_to_point(6, 11)` 会返回 (6, 11) 像素的左上角
        - 例如 `.pixel_to_point(6.5, 11.5)` 会返回 (6, 11) 像素的中心
        '''
        hor = self.get_horizontal_vect()
        ver = self.get_vertical_vect()
        orig = self.get_orig()
        width, height = self.texture.img.size().toTuple()

        return orig + hor * x / width + ver * y / height

    def set_opacity(self, opacity: float | Iterable[float]) -> Self:
        self.set_points_color(opacity=opacity)
        return self
    
class PixelImgItem(ImgItem):
    min_mag_filter = QOpenGLTexture.Filter.Nearest
