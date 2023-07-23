from __future__ import annotations
from typing import Iterable

import freetype as FT

from janim.constants import *
from janim.config import get_configuration
from janim.items.item import Item
from janim.items.vitem import VItem, VGroup
from janim.utils.font import get_fontpath_by_name, get_font_face
from janim.utils.functions import decode_utf8


class TextChar(VItem):
    def __init__(self, char: str, fonts: list[FT.Face], **kwargs) -> None:
        super().__init__(**kwargs)
        self.char = char

        unicode = decode_utf8(char)

        # 确定使用的字体
        face_render = fonts[0]
        for face in fonts:
            idx = face.get_char_index(unicode)
            if idx != 0:
                face_render = face
                break
        
        # 读取字符
        face_render.load_char(char, FT.FT_LOAD_DEFAULT | FT.FT_LOAD_NO_BITMAP)
        glyph: FT.Glyph = face.glyph
        outline: FT.Outline = glyph.outline

        def f(p) -> np.ndarray:
            return np.array([p.x, p.y, 0])
        
        def move_to(v_point, _):
            self.path_move_to(f(v_point))

        def line_to(v_point, _):
            self.add_line_to(f(v_point))   

        def conic_to(v_handle, v_point, _):
            self.add_conic_to(f(v_handle), f(v_point))   

        def cubic_to(v_handle1, v_handle2, v_end, _):
            raise NotImplementedError('Cubic curve is not supported')
        
        # 解析轮廓
        outline.decompose(outline, move_to, line_to, conic_to, cubic_to)
        self.subdivide_sharp_curves()

        # 标记位置
        self.mark = Item()
        self.mark.set_points([
            ORIGIN, RIGHT, UP,
            [glyph.advance.x, glyph.advance.y, 0]
        ])
        self.add(self.mark, is_helper=True)

        self.scale(PIXEL_TO_FRAME_RATIO / 32, False, about_point=ORIGIN)
    
    def get_mark_orig(self) -> np.ndarray:
        return self.mark.get_points()[0]
    
    def get_mark_right(self) -> np.ndarray:
        return self.mark.get_points()[1]
    
    def get_mark_up(self) -> np.ndarray:
        return self.mark.get_points()[2]
    
    def get_mark_advance(self) -> np.ndarray:
        return self.mark.get_points()[3]
    
class TextLine(VGroup):
    def __init__(self, text: str, fonts: list[FT.Face], **kwargs) -> None:
        self.text = text

        super().__init__(
            *[
                TextChar(char, fonts=fonts)
                for char in text
            ],
            **kwargs
        )
        self.arrange_for_line()

        # 标记位置
        self.mark = Item()
        self.mark.set_points([ORIGIN, RIGHT, UP])
        self.add(self.mark, is_helper=True)

    def get_mark_orig(self) -> np.ndarray:
        return self.mark.get_points()[0]

    def get_mark_right(self) -> np.ndarray:
        return self.mark.get_points()[1]

    def get_mark_up(self) -> np.ndarray:
        return self.mark.get_points()[2]
    
    def arrange_for_line(self) -> None:
        if len(self.items) == 0:
            return
        
        pos = self[0].get_mark_advance()
        for char in self[1:]:
            char.shift(pos - char.get_mark_orig())
            pos = char.get_mark_advance()


class Text(VGroup):
    def __init__(
        self, 
        text: str, 
        font: str | Iterable[str] = [],
        fill_color: JAnimColor = WHITE,
        fill_opacity: float = 1.0,
        stroke_width: float = 0,
        **kwargs
    ) -> None:
        self.text = text

        # 获取字体
        if isinstance(font, str):
            font = [font]
        font.append(get_configuration()['style']['font'])
        font = [
            get_font_face(get_fontpath_by_name(name)) 
            for name in font
        ]

        super().__init__(
            *[
                TextLine(line_text, fonts=font) 
                for line_text in text.split('\n')
            ],
            fill_opacity=fill_opacity,
            stroke_width=stroke_width,
            **kwargs
        )
        self.set_fill(fill_color, fill_opacity)
        self.set_stroke_width(stroke_width)

        self.arrange_for_lines()
        self.to_center()
        
    def arrange_for_lines(self, buff=0.7) -> None:
        if len(self.items) == 0:
            return
        
        pos = self[0].get_mark_orig()
        vert = pos - self[0].get_mark_up()
        for line in self[1:]:
            line.shift((pos + buff * vert) - line.get_mark_orig())
            pos = line.get_mark_orig()
            vert = pos - line.get_mark_up()


