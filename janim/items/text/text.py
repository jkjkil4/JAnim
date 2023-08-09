from __future__ import annotations
from typing import Iterable, Optional
from janim.typing import Self

import re

from janim.constants import *
from janim.config import get_configuration
from janim.items.item import Item, Group
from janim.items.vitem import VItem, VGroup
from janim.utils.font import Font, get_fontpath_by_name
from janim.utils.functions import decode_utf8
from janim.utils.space_ops import normalize, get_norm

DEFAULT_FONT_SIZE = 24
ORIG_FONT_SIZE = 48

class _VTextChar(VItem):
    def __init__(self, char: str, fonts: list[Font], font_size: float, **kwargs) -> None:
        super().__init__(**kwargs)
        self.char = char

        unicode = decode_utf8(char)
        font_render = self.get_font_for_render(unicode, fonts)
        
        outline, advance = font_render.get_glyph_data(unicode)
        self.set_points(outline)

        # 缩放
        font_scale_factor = font_size / ORIG_FONT_SIZE
        frame_scale_factor = PIXEL_TO_FRAME_RATIO / 32
        scale_factor = font_scale_factor * frame_scale_factor
        self.scale(scale_factor, False, about_point=ORIGIN)

        # 标记位置
        self.mark = Item()
        self.mark.set_points([
            ORIGIN, RIGHT * font_scale_factor, UP * font_scale_factor,
            [advance[0] * scale_factor, advance[1] * scale_factor, 0]
        ])
        self.add(self.mark, is_helper=True)
    
    @staticmethod
    def get_font_for_render(unicode: str, fonts: list[Font]) -> Font:
        font_render = fonts[0]
        for font in fonts:
            idx = font.face.get_char_index(unicode)
            if idx != 0:
                font_render = font
                break
        return font_render
    
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
    
    @staticmethod
    def check_act_arg_count(act: Iterable[str], count: int | Iterable[int]) -> int:
        if isinstance(count, int):
            count = (count, )
        
        for cnt in count:
            if len(act) == 1 + cnt:
                return cnt
        args_cnt = ' or '.join(count)
        raise TypeError(f'{act[0]} takes {args_cnt} arguments but {len(act) - 1} was given')
    
    @staticmethod
    def get_attr_from_act_list(act_list: list[Iterable[str]], key: str) -> Iterable[str] | None:
        for act in reversed(act_list):
            if act[0] == key:
                return act
        return None
    
    def apply_act_list(self, act_list: list[Iterable[str]]) -> None:
        color = self.get_attr_from_act_list(act_list, 'c')
        if color:
            arg_cnt = self.check_act_arg_count(color, (1, 3, 4))
            if arg_cnt == 1:
                _, color_key = color
                import janim.constants.colors as colors
                if not hasattr(colors, color_key):
                    raise ValueError(f'no built-in color named {color_key}')
                self.set_color(getattr(colors, color_key))
            elif arg_cnt == 3:
                self.set_color([float(val) for val in color[1:]])
            else:   # == 4
                self.set_rgbas([[float(val) for val in color[1:]]])
        
        opacity = self.get_attr_from_act_list(act_list, 'opacity')
        if opacity:
            self.check_act_arg_count(opacity, 1)
            self.set_opacity(float(opacity[1]))


class _TextLine(Group):
    CharClass = _VTextChar

    def __init__(self, text: str, fonts: list[Font], font_size: float, char_kwargs = {}, **kwargs) -> None:
        self.text = text

        super().__init__(
            *[
                self.CharClass(char, fonts=fonts, font_size=font_size, **char_kwargs)
                for char in text
            ],
            **kwargs
        )
        self.arrange_in_line()

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
    
    def arrange_in_line(self, buff: float = 0) -> Self:
        if len(self.items) == 0:
            return
        
        pos: np.ndarray = None
        def update(char: _VTextChar) -> None:
            nonlocal pos
            orig = char.get_mark_orig()
            advance = char.get_mark_advance()
            pos = advance if buff == 0 else advance + buff * normalize(advance - orig)

        update(self[0])
        for char in self[1:]:
            char.shift(pos - char.get_mark_orig())
            update(char)

        return self
    
class _VTextLine(_TextLine, VGroup):
    pass


class _Text(Group):
    LineClass = _VTextLine

    class Format(Enum):
        PlainText = 0
        RichText = 1

    def __init__(
        self, 
        text: str, 
        font: str | Iterable[str] = [],
        font_size: float = DEFAULT_FONT_SIZE,
        format: Format = Format.PlainText,
        line_kwargs = {},
        **kwargs
    ) -> None:
        # 获取字体
        if isinstance(font, str):
            font = [font]
        font.append(get_configuration()['style']['font'])
        fonts = [
            Font.get(get_fontpath_by_name(name)) 
            for name in font
        ]

        if not format == _Text.Format.RichText:
            self.text = text
        else:
            # 如果是 RichText，获取属性列表
            self.text = ''
            self.act_list: list[tuple[int, list[str, str] | str]] = []
            idx = 0
            iter = re.finditer(r'(<+)(/?[^<]*?)>', text, re.RegexFlag.MULTILINE)
            for match in iter:
                match: re.Match
                start, end = match.span()
                left, mid = match.group(1, 2)

                self.text += text[idx:start]
                idx = end

                left_cnt = len(left)
                self.text += '<' * (left_cnt // 2)
                if left_cnt % 2 == 0:
                    self.text += mid + '>'
                else:
                    self.act_list.append((
                        len(self.text), 
                        mid[1:] if mid.startswith('/') else mid.split()
                    ))
                    
            self.text += text[idx:]

        super().__init__(
            *[
                self.LineClass(line_text, fonts=fonts, font_size=font_size, **line_kwargs) 
                for line_text in self.text.split('\n')
            ],
            **kwargs
        )
                            
        self.arrange_in_lines()
        self.to_center()
        
    def arrange_in_lines(self, buff: float = 0, base_buff: float = 0.85) -> Self:
        '''
        - `buff`: 每行之间的额外间距
        - `base_buff`: 每行之间的基本间距，默认值 `0.85` 用于将两行上下排列，如果是 `0` 则会让两行完全重合，大部分时候不需要传入该值
        '''
        if len(self.items) == 0:
            return
        
        pos: np.ndarray = None
        vert: np.ndarray = None
        def update(line: _TextLine) -> None:
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
    ) -> Self:
        '''
        - `break_length`: 自动换行的宽度，若某一行的宽度超过该值，则会将超出部分向下换行
        - `stretch`: 拆行后，是否进行左右对齐，以填补两侧边界可能出现的不规则空隙
        - `buff`, `base_buff`: 参照 `arrange_in_lines()`
        - `center`: 是否在完成后将物体移动至原点
        '''
        new_lines: tuple[_TextLine, list[_VTextChar], bool] = []

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
            new_line: list[_VTextChar] = []
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
            line = self.LineClass('', [], DEFAULT_FONT_SIZE)
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
                line.arrange_in_line(space_length)

            new_lines_items.append(line)

        self.remove(*self.items)
        self.add(*new_lines_items)
        self.arrange_in_lines(buff, base_buff)
        if center:
            self.to_center()
        return self
    
    def apply_rich_text(self) -> None:
        text_at = 0
        act_idx = 0
        act_stack = []
        for line in self:
            for char in line:
                while act_idx < len(self.act_list):
                    next_act_at, next_act = self.act_list[act_idx]
                    if text_at < next_act_at:
                        break

                    if not isinstance(next_act, str):
                        act_stack.append(next_act)
                    else:
                        found = False
                        while len(act_stack) > 0 and not found:
                            found = act_stack[-1][0] == next_act
                            act_stack.pop()
                    act_idx += 1

                char.apply_act_list(act_stack)
                text_at += 1
                
            text_at += 1
    
class Text(_Text, VGroup):
    '''
    文字物件

    - 文字的子物件 `text[i]` 是文字的每一行
    - 每行的子物件 `line[i]` 是文字的每个字符

    例如 `text[1][0]` 是第二行的首个字符

    可以调用 `word_wrap()` 进行自动换行（拆行） 
    '''
    def __init__(
        self, 
        text: str, 
        font: str | Iterable[str] = [],
        font_size: float = DEFAULT_FONT_SIZE,
        color: JAnimColor = WHITE,
        opacity: float = 1.0,
        stroke_width: Optional[float] = None,
        format: _Text.Format = _Text.Format.PlainText,
        **kwargs
    ) -> None:
        if stroke_width is None:
            stroke_width = font_size / ORIG_FONT_SIZE * 0.0075

        super().__init__(text, font, font_size, format=format, **kwargs)

        self.set_color(color, opacity)
        self.set_stroke_width(stroke_width)

        if format == _Text.Format.RichText:
            self.apply_rich_text()
