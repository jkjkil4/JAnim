
import math
from typing import Iterable, Optional
from janim.typing import Self

from PySide6.QtGui import QMatrix4x4
from PySide6.QtOpenGL import QOpenGLFramebufferObject

from OpenGL.GL import GL_RGBA, glViewport

from janim.constants import *
from janim.constants import Iterable, JAnimColor
from janim.items.img_item import PixelImgItem
from janim.items.text.text import DEFAULT_FONT_SIZE, ORIG_FONT_SIZE, _VTextChar, _TextLine, _Text
from janim.utils.font import Font
from janim.scene.scene import Scene
from janim.utils.space_ops import get_norm

from janim.gl.render import RenderData

PIXELTEXT_FONTSIZE_STEP = 12
PIXELTEXT_FONTSIZE_EXT = 18

class _PixelTextChar(PixelImgItem):
    def __init__(self, char: str, fonts: list[Font], font_size: float, stroke_width: float, **kwargs) -> None:
        self.char = char

        sketchy_font_size = math.ceil(font_size / PIXELTEXT_FONTSIZE_STEP) * PIXELTEXT_FONTSIZE_STEP + PIXELTEXT_FONTSIZE_EXT
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
    
    def apply_act_list(self, act_list: list[Iterable[str]]) -> None:
        def method_color(color) -> None:
            arg_cnt = _VTextChar.check_act_arg_count(color, (1, 3, 4))
            if arg_cnt == 1:
                _, color_key = color
                import janim.constants.colors as colors
                if not hasattr(colors, color_key):
                    raise ValueError(f'no built-in color named {color_key}')
                self.set_points_color(getattr(colors, color_key))
            elif arg_cnt == 3:
                self.set_points_color([float(val) for val in color[1:]])
            else:   # == 4
                self.set_rgbas([[float(val) for val in color[1:]]])
        
        def method_opacity(opacity) -> None:
            _VTextChar.check_act_arg_count(opacity, 1)
            self.set_opacity(float(opacity[1]))

        methods = {
            'c': method_color,
            'opacity': method_opacity
        }

        for act in reversed(act_list):
            method = methods.get(act[0])
            if method:
                del methods[act[0]]
                method(act)
            if len(methods) == 0:
                break

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
        stroke_width: float = None,
        format: _Text.Format = _Text.Format.PlainText,
        **kwargs
    ) -> None:
        if stroke_width is None:
            stroke_width = font_size / ORIG_FONT_SIZE * 0.0075
        super().__init__(
            text, 
            font, 
            font_size, 
            format=format,
            line_kwargs={ 'char_kwargs': { 'stroke_width': stroke_width } }, 
            **kwargs
        )

        self.set_points_color(color, opacity)

        if format == _Text.Format.RichText:
            self.apply_rich_text()

