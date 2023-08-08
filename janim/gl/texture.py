from __future__ import annotations

import weakref

from PySide6.QtGui import QImage
from PySide6.QtOpenGL import QOpenGLTexture

class Texture(QOpenGLTexture):
    '''
    简单封装，读取给定位置的图像文件

    使用 `Texture.get(filename)` 获取着色器对象可以便于复用
    '''

    single_texture_to_destroy: list[weakref.ref[Texture]] = []

    # 存储可复用的纹理对象
    filepath_to_texture_map: dict[str, Texture] = {}

    @staticmethod
    def get(filepath: str, minMagFilter: QOpenGLTexture.Filter) -> Texture:
        '''
        若 `filename` 对应纹理先前已创建过，则复用先前的对象，否则另外创建新的对象
        '''
        key = (filepath, minMagFilter)
        if key in Texture.filepath_to_texture_map:
            return Texture.filepath_to_texture_map[key]
        
        texture = Texture(filepath, minMagFilter)
        Texture.filepath_to_texture_map[key] = texture
        return texture

    @staticmethod
    def release_all() -> None:
        for r in Texture.single_texture_to_destroy:
            texture = r()
            if texture is not None:
                texture.destroy()
        Texture.single_texture_to_destroy.clear()

        for texture in Texture.filepath_to_texture_map.values():
            texture.destroy()
        Texture.filepath_to_texture_map.clear()
    
    def __init__(self, filename_or_img: str | QImage, minMagFilter: QOpenGLTexture.Filter) -> None:
        super().__init__(QOpenGLTexture.Target.Target2D)

        if isinstance(filename_or_img, QImage):
            self.img = filename_or_img
            Texture.single_texture_to_destroy.append(weakref.ref(self))
        else:
            self.img = QImage(filename_or_img)
            if self.img.isNull():
                raise ValueError(f'图像路径 "{filename_or_img}" 无效')

        self.create()
        self.setData(self.img)
        self.setMinMagFilters(QOpenGLTexture.Filter.Linear, minMagFilter)
        self.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)
