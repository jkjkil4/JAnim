from __future__ import annotations
from typing import Iterable

import freetype as FT

from janim.constants import *
from janim.config import get_configuration
from janim.items.item import Item
from janim.items.vitem import VItem, VGroup
from janim.utils.font import get_fontpath_by_name, get_font_face
from janim.utils.functions import decode_utf8
from janim.utils.space_ops import normalize, get_norm

DEFAULT_FONT_SIZE = 24
ORIG_FONT_SIZE = 48

class TextChar(VItem):
    def __init__(self, char: str, fonts: list[FT.Face], font_size: float, **kwargs) -> None:
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

        font_scale_factor = font_size / ORIG_FONT_SIZE
        frame_scale_factor = PIXEL_TO_FRAME_RATIO / 32
        scale_factor = font_scale_factor * frame_scale_factor
        self.scale(scale_factor, False, about_point=ORIGIN)

        # 标记位置
        self.mark = Item()
        self.mark.set_points([
            ORIGIN, RIGHT * font_scale_factor, UP * font_scale_factor,
            [glyph.advance.x * scale_factor, glyph.advance.y * scale_factor, 0]
        ])
        self.add(self.mark, is_helper=True)
    
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

class TextLine(VGroup):
    CharClass = TextChar

    def __init__(self, text: str, fonts: list[FT.Face],font_size: float, **kwargs) -> None:
        self.text = text

        super().__init__(
            *[
                self.CharClass(char, fonts=fonts, font_size=font_size)
                for char in text
            ],
            **kwargs
        )
        self.arrange_for_line()

        # 标记位置
        self.mark = Item()
        self.mark.set_points([ORIGIN, RIGHT, UP])
        self.mark.scale(font_size / ORIG_FONT_SIZE, about_point=ORIGIN)
        self.add(self.mark, is_helper=True)

    def get_mark_orig(self) -> np.ndarray:
        return self.mark.get_points()[0]

    def get_mark_right(self) -> np.ndarray:
        return self.mark.get_points()[1]

    def get_mark_up(self) -> np.ndarray:
        return self.mark.get_points()[2]
    
    def arrange_for_line(self, buff: float = 0) -> None:
        if len(self.items) == 0:
            return
        
        pos: np.ndarray = None
        def update(char: TextChar) -> None:
            nonlocal pos
            orig = char.get_mark_orig()
            advance = char.get_mark_advance()
            pos = advance if buff == 0 else advance + buff * normalize(advance - orig)

        update(self[0])
        for char in self[1:]:
            char.shift(pos - char.get_mark_orig())
            update(char)

        return self


class Text(VGroup):
    LineClass = TextLine

    def __init__(
        self, 
        text: str, 
        font: str | Iterable[str] = [],
        font_size: float = DEFAULT_FONT_SIZE,
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
                self.LineClass(line_text, fonts=font, font_size=font_size) 
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
        
    def arrange_for_lines(self, buff: float = 0, base_buff: float = 0.85) -> None:
        if len(self.items) == 0:
            return
        
        pos: np.ndarray = None
        vert: np.ndarray = None
        def update(line: TextLine) -> None:
            nonlocal pos, vert
            pos = line.get_mark_orig()
            vert = pos - line.get_mark_up()

        update(self[0])
        for line in self[1:]:
            line.shift((pos + base_buff * vert + buff * normalize(vert)) - line.get_mark_orig())
            update(line)
        
        return self
    
    def word_wrap(
        self, 
        break_length: float = FRAME_WIDTH - 2 * DEFAULT_ITEM_TO_EDGE_BUFF,
        stretch: bool = True,
        buff: float = 0,
        base_buff: float = 0.85,
        center: bool = True
    ):
        new_lines: tuple[TextLine, list[TextChar], bool] = []

        # 遍历每行
        for line in self:
            # 如果该行没有字符，则跳过
            if len(line) == 0:
                new_lines.append((line, [], True))
                continue

            # left 记录当前新行的最左侧位置
            # new_line 记录当前新行所包含的字符
            # eol (end of line) 记录当前新行是否是原来行的结尾
            left: np.ndarray = None
            new_line: list[TextChar] = []
            eol = False

            # 用于将 new_line 添加到 new_lines 中，并重置状态
            def emit_line() -> None:
                nonlocal left, new_line
                new_lines.append((line, new_line, eol))
                left = None
                new_line = []

            # 遍历每个字符，计算前后距离，进行拆行
            for char in line:
                if left is None:
                    left = char.get_mark_orig()
                if char is line[-1]:
                    eol = True
                
                # 得到当前位置右侧与新行最左侧位置的距离
                length = get_norm(char.get_mark_advance() - left)

                # 如果是第一个字符，那么先添加再判断是否拆行，否则先判断再添加
                if len(new_line) == 0:
                    new_line.append(char)
                    if length > break_length:
                        emit_line()
                else:
                    if length > break_length:
                        emit_line()
                    new_line.append(char)
            
            # 保证末尾字符进入 new_lines
            if len(new_line) > 0:
                emit_line()

        # 遍历 new_lines，生成新的行物件
        new_lines_items = []
        for orig_line, new_line, eol in new_lines:
            # 生成空 TextLine 物件，并复制原来行的位置标记
            line = TextLine('', [], DEFAULT_FONT_SIZE)
            line.mark.set_points(orig_line.mark.get_points())

            # 如果该行为空，则直接添加
            if len(new_line) == 0:
                new_lines_items.append(line)
                continue

            # 构建数据
            line.text = ''.join(item.char for item in new_line)                 # 将所有字符文字组合为 line.text
            line.add(*new_line)                                                 # 将所有字符添加到 line 中
            line.mark.shift(line[0].get_mark_orig() - line.get_mark_orig())     # 正确放置 line 的标记

            # 如果需要左右对齐，且不是原来行的行尾，且新行不止一个字符，则进行对齐
            if stretch and not eol and len(line) > 1:
                total_advance_length = sum([char.get_advance_length() for char in line])
                total_space_length = break_length - total_advance_length
                space_length = total_space_length / (len(line) - 1)
                line.arrange_for_line(space_length)

            new_lines_items.append(line)

        self.remove(*self.items)
        self.add(*new_lines_items)
        self.arrange_for_lines(buff, base_buff)
        if center:
            self.to_center()
        return self


