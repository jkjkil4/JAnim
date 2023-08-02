from __future__ import annotations

from PySide6.QtGui import QImage
from PySide6.QtOpenGL import QOpenGLTexture

class Texture(QOpenGLTexture):
    '''
    简单封装，读取给定位置的图像文件

    使用 `Texture.get(filename)` 获取着色器对象可以便于复用
    '''

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
    
    def release_all() -> None:
        for texture in Texture.filepath_to_texture_map.values():
            texture.destroy()
        Texture.filepath_to_texture_map.clear()
    
    def __init__(self, filename: str, minMagFilter: QOpenGLTexture.Filter) -> None:
        super().__init__(QOpenGLTexture.Target.Target2D)

        self.img = QImage(filename)
        if self.img.isNull():
            raise ValueError(f'图像路径 "{filename}" 无效')

        self.create()
        self.setData(self.img)
        self.setMinMagFilters(QOpenGLTexture.Filter.Linear, minMagFilter)
        self.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)
