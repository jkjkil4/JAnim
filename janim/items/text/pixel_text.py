
import math

from PySide6.QtGui import QMatrix4x4
from PySide6.QtOpenGL import QOpenGLTexture, QOpenGLFramebufferObject

from OpenGL.GL import *

from janim.constants import *
from janim.items.img_item import PixelImgItem
from janim.items.text.text import DEFAULT_FONT_SIZE, ORIG_FONT_SIZE, _VTextChar, _TextLine, _Text
from janim.utils.font import Font
from janim.scene.scene import Scene, Camera
from janim.utils.space_ops import get_norm

from janim.gl.render import RenderData

PIXELTEXT_FONTSIZE_STEP = 24

class _PixelTextChar(PixelImgItem):
    def __init__(self, char: str, fonts: list[Font], font_size: float, stroke_width: float, **kwargs) -> None:
        self.char = char

        sketchy_font_size = math.ceil(font_size / 12) * 12 + 18
        txt = _VTextChar(char, fonts, sketchy_font_size, stroke_width=stroke_width).set_fill(opacity=1)

        width, height = txt.get_width() + 0.1, txt.get_height() + 0.1
        f_width, f_height = math.ceil(width / PIXEL_TO_FRAME_RATIO), math.ceil(height / PIXEL_TO_FRAME_RATIO)
        
        iden = QMatrix4x4()
        iden.setToIdentity()
        
        wnd = QMatrix4x4()
        wnd.setToIdentity()
        wnd.scale(2 / (f_width * PIXEL_TO_FRAME_RATIO), 2 / (f_height * PIXEL_TO_FRAME_RATIO))
        wnd.translate(*(-txt.get_center()))

        fbo = QOpenGLFramebufferObject(
            f_width, f_height,
            QOpenGLFramebufferObject.Attachment.NoAttachment,
            internalFormat=GL_RGBA
        )

        fbo.bind()

        glViewport(0, 0, f_width, f_height)
        txt.render(RenderData(
            Scene.anti_alias_width, 
            (1920, 1080), 
            iden, iden, wnd
        ))

        fbo.release()

        super().__init__(fbo.toImage(), **kwargs)
        self.shift(txt.get_center())
        
        self.mark = txt.mark
        self.add(self.mark, is_helper=True)

        self.scale(font_size / sketchy_font_size, about_point=ORIGIN)
    
    def get_mark_orig(self) -> np.ndarray:
        return self.mark.get_points()[0]
    
    def get_mark_right(self) -> np.ndarray:
        return self.mark.get_points()[1]
    
    def get_mark_up(self) -> np.ndarray:
        return self.mark.get_points()[2]
    
    def get_mark_advance(self) -> np.ndarray:
        return self.mark.get_points()[3]
    
    def get_advance_length(self) -> float:
        return get_norm(self.get_mark_advance() - self.get_mark_orig())

class _PixelTextLine(_TextLine):
    CharClass = _PixelTextChar

class PixelText(_Text):
    LineClass = _PixelTextLine

    def __init__(
        self, 
        text: str, 
        font: str | Iterable[str] = [],
        font_size: float = DEFAULT_FONT_SIZE,
        color: JAnimColor = WHITE,
        opacity: float = 1.0,
        stroke_width: float = None
    ) -> None:
        if stroke_width is None:
            stroke_width = font_size / ORIG_FONT_SIZE * 0.0075
        super().__init__(text, font, font_size, line_kwargs={ 'char_kwargs': { 'stroke_width': stroke_width } })
        self.set_points_color(color, opacity)
