from __future__ import annotations

from PySide6.QtGui import QImage
from PySide6.QtOpenGL import QOpenGLTexture

class Texture(QOpenGLTexture):
    '''
    简单封装，读取给定位置的图像文件

    使用 `Texture.get(filename)` 获取着色器对象可以便于复用
    '''

    # TODO: 解决提示信息: `QOpenGLTexturePrivate::destroy() called without a current context. Texture has not been destroyed`

    # 存储可复用的纹理对象
    filename_to_texture_map = {}

    @staticmethod
    def get(filename: str) -> Texture:
        '''
        若 `filename` 对应纹理先前已创建过，则复用先前的对象，否则另外创建新的对象
        '''

        if filename in Texture.filename_to_texture_map:
            return Texture.filename_to_texture_map[filename]
        
        texture = Texture(filename)
        Texture.filename_to_texture_map[filename] = texture
        return texture
    
    def __init__(self, filename: str) -> None:
        super().__init__(QOpenGLTexture.Target.Target2D)

        self.img = QImage(filename)
        if self.img.isNull():
            raise ValueError(f'图像路径 "{filename}" 无效')

        self.create()
        self.setData(self.img)
        self.setMinMagFilters(QOpenGLTexture.Filter.Linear, QOpenGLTexture.Filter.Linear)
        self.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)
