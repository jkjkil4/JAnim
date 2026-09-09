from __future__ import annotations

import inspect
import itertools as it
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable, Literal, Self

import numpy as np

from janim.components.component import CmptInfo
from janim.components.points import Cmpt_Points
from janim.constants import DL, DOWN, DR, GREY, LEFT, MED_SMALL_BUFF, ORIGIN, RIGHT, UL, UP, UR
from janim.items.geometry.line import Line
from janim.items.group import Group
from janim.items.item import Item
from janim.items.points import MarkedItem, Points
from janim.items.text.cmpt import (
    Cmpt_Mark_TextCharImpl,
    Cmpt_Mark_TextLineImpl,
)
from janim.items.text.rich import TagQueue, extract_tag_queue
from janim.items.vitem import VItem
from janim.render.renderer.r_textchar import PixelRenderInfo, TextCharRenderer
from janim.typing import Vect
from janim.utils.config import Config
from janim.utils.font.database import ORIG_FONT_SIZE, Font, get_font_info_by_attrs
from janim.utils.font.variant import Style, StyleName, Weight, WeightName
from janim.utils.simple_functions import decode_utf8
from janim.utils.space_ops import cross, get_norm, normalize

__all__ = [
    'BASEPOINT_MARKS',
    'DEFAULT_FONT_SIZE',
    'ORIG_FONT_SIZE',
    'ProjType',
    'BasepointVItem',
    'TextChar',
    'TextLine',
    'Text',
    'Title',
    'SourceDisplayer',
]

BASEPOINT_MARKS = np.array([ORIGIN, RIGHT, UP])
BASEPOINT_MARKS.setflags(write=False)

DEFAULT_FONT_SIZE = 24


class ProjType(StrEnum):
    Horizontal = 'horizontal'
    Vertical = 'vertial'
    H = 'h'
    V = 'v'


class BasepointVItem(MarkedItem, VItem):
    def offset_to(
        self,
        other: BasepointVItem,
        proj: ProjType | Literal['horizontal', 'vertical', 'h', 'v'] | Vect | None = None,
    ) -> np.ndarray:
        """
        计算从 ``self`` 到 ``other`` 的偏移量，如果指定了 ``proj`` 则只计算在该方向上的投影量

        例如当我们想要让一段文字和另一段文字的基线对齐，可以使用 ``.offset_to(other, 'v')`` 计算基线垂直方向的偏移量，从而根据该量移动来对齐基线。
        """
        # 假定 [0] 是 basepoint，[1] 是 right，[2] 是 up
        offset = other.mark.get(0) - self.mark.get(0)
        if proj is None:
            return offset

        match proj:
            case ProjType.Horizontal | ProjType.H:
                proj_vect = self.mark.get(1) - self.mark.get(0)
            case ProjType.Vertical | ProjType.V:
                proj_vect = self.mark.get(2) - self.mark.get(0)
            case _:
                proj_vect = np.array(proj)

        scalar = np.dot(offset, proj_vect) / np.dot(proj_vect, proj_vect)
        return scalar * proj_vect

    def matrix_of_marks(self) -> np.matrix:
        """
        得到标记点的坐标标架构成的矩阵
        """
        # 假定 [0] 是 basepoint，[1] 是 right，[2] 是 up
        right = self.mark.get(1) - self.mark.get(0)
        up = self.mark.get(2) - self.mark.get(0)
        normal = np.array(cross(right, up)) / get_norm(up)
        return np.matrix([right, up, normal]).T


class TextChar(BasepointVItem):
    """
    字符物件，作为 :class:`TextLine` 的子物件，在创建 :class:`TextLine` 时产生
    """

    renderer_cls = TextCharRenderer

    mark = CmptInfo(Cmpt_Mark_TextCharImpl[Self])

    def __init__(
        self,
        char: str,
        params: _TextParams,
        fill_alpha=None,
        **kwargs,
    ):
        super().__init__(fill_alpha=fill_alpha, **kwargs)
        self.char = char

        unicode = decode_utf8(char)
        font_render = self.get_font_for_render(unicode, params.fonts)

        outline, advance = font_render.get_glyph_data(unicode)

        # 因为 get_glyph_data 得到的字形是 font_size=48 的字形（具体参考 janim.utils.font.Font.__init__ 中的 set_char_size）
        # 所以这里使用 font_size / ORIG_FONT_SIZE 缩放到目标字号
        font_scale_factor = params.font_size / ORIG_FONT_SIZE
        # frame_scale_factor 中包含了两个缩放因素：
        # - 1/64：
        #       这是因为使用 get_glyph_data 得到的字形坐标仍然是 26.6 数值格式，所以需要右移 6 位也就是除以 64
        # - Config.get.default_pixel_to_frame_ratio:
        #       在使用 1/64 缩放后，得到的是像素大小，还需要使用 pixel_to_frame 进行转换
        frame_scale_factor = Config.get.default_pixel_to_frame_ratio / 64

        scale_factor = font_scale_factor * frame_scale_factor

        scaled_outline = outline * scale_factor

        if params.is_pixel_render:
            self._pixel_render_info = PixelRenderInfo(unicode, outline, params.font_size)
            box = Cmpt_Points.BoundingBox(scaled_outline)
            self.points.set([box.get(DL), box.get(DR), box.get(UR), box.get(UL), box.get(DL)])
        else:
            self._pixel_render_info = None
            self.points.set(scaled_outline)

        # 标记位置
        self.mark.set_points(
            [
                ORIGIN,
                RIGHT * font_scale_factor,
                UP * font_scale_factor,
                [advance[0] * scale_factor, advance[1] * scale_factor, 0],
            ]
        )

    @staticmethod
    def get_font_for_render(unicode: str, fonts: list[Font]) -> Font:
        """
        从字体列表中找到支持显示 ``unicode`` 的字体，如果找不到只好选用第一个
        """
        font_render = fonts[0]
        for font in fonts:
            idx = font.face.get_char_index(unicode)
            if idx != 0:
                font_render = font
                break
        return font_render

    def become(self, other: Item, *, auto_visible: bool = True) -> Self:
        super().become(other, auto_visible=auto_visible)
        if isinstance(other, TextChar):
            self._pixel_render_info = other._pixel_render_info
        else:
            self._pixel_render_info = None
        return self

    def get_mark_orig(self) -> np.ndarray:
        return self.mark.get(0)

    def get_mark_right(self) -> np.ndarray:
        return self.mark.get(1)

    def get_mark_up(self) -> np.ndarray:
        return self.mark.get(2)

    def get_mark_advance(self) -> np.ndarray:
        return self.mark.get(3)

    def get_advance_length(self) -> float:
        return get_norm(self.get_mark_advance() - self.get_mark_orig())


class TextLine(BasepointVItem, Group[TextChar]):
    """
    单行文字物件，作为 :class:`Text` 的子物件，在创建 :class:`Text` 时产生
    """

    mark = CmptInfo(Cmpt_Mark_TextLineImpl[Self])

    def __init__(
        self,
        text: str,
        params: _TextParams,
        *,
        char_kwargs={},
        fill_alpha=None,
        **kwargs,
    ):
        self.text = text

        super().__init__(
            *[TextChar(char, params, **char_kwargs) for char in text],
            fill_alpha=fill_alpha,
            **kwargs,
        )

        # 标记位置
        scale = params.font_size / ORIG_FONT_SIZE
        self.mark.set_points([ORIGIN * scale, RIGHT * scale, UP * scale])

    def get_mark_orig(self) -> np.ndarray:
        return self.mark.get(0)

    def get_mark_right(self) -> np.ndarray:
        return self.mark.get(1)

    def get_mark_up(self) -> np.ndarray:
        return self.mark.get(2)

    def arrange_in_line(self, buff: float = 0) -> Self:
        """
        根据 ``advance`` 的标记信息排列该行
        """
        if len(self) == 0:
            return self

        pos = None

        for i, char in enumerate(self):
            if i != 0:
                char.points.shift(pos - char.get_mark_orig())

            orig = char.get_mark_orig()
            advance = char.get_mark_advance()
            pos = advance if buff == 0 else advance + buff * normalize(advance - orig)

        return self

    def match_to(self, target: Text | TextLine) -> Self:
        """
        将该行文本与目标文本或文本行对齐

        :param target: 目标文本或文本行
        """
        line = target if isinstance(target, TextLine) else target[0]
        TextLine._match_to(self, self, line)
        return self

    @staticmethod
    def _match_to(item: Points, line1: TextLine, line2: TextLine) -> None:
        mat = line2.matrix_of_marks() @ line1.matrix_of_marks().I

        # fmt: off
        item.points.shift(-line1.mark.get()) \
                   .apply_matrix(mat) \
                   .shift(line2.mark.get())
        # fmt: on


@dataclass(slots=True)
class _TextParams:
    fonts: list[Font]
    font_size: float
    is_pixel_render: bool


class Text(Group[TextLine], VItem):
    """
    文字物件，支持富文本等功能

    如果对换行排版等有较高的需求可以考虑使用 :class:`~.TypstDoc` 以及 :class:`~.TypstText`

    示例：

    .. code-block:: python

        Text('Hello World!')

    .. code-block:: python

        Text('Hello <c RED>World</c>!', format='rich')
    """

    class Format(StrEnum):
        PlainText = 'plain'
        RichText = 'rich'

    class Render(StrEnum):
        VItemText = 'vitem'
        PixelText = 'pixel'

    def __init__(
        self,
        text: str,
        # -
        font: str | Iterable[str] = [],
        font_size: float = DEFAULT_FONT_SIZE,
        weight: int | Weight | WeightName = 400,  # = 'regular'
        style: Style | StyleName = Style.Normal,
        force_full_name: bool = False,  # 一般情况下用不到，只是为了在 family-name 调用不符合预期时，使用该参数强制作为 full-name
        # -
        format: Format | Literal['plain', 'rich'] = Format.PlainText,
        render: Render | Literal['vitem', 'pixel'] = Render.VItemText,
        line_kwargs: dict = {},
        # -
        stroke_alpha: float = 0,
        fill_alpha: float = 1,
        stroke_background: bool = True,
        # -
        center: bool = True,
        **kwargs,
    ) -> None:
        # 获取字体
        if isinstance(font, str):
            font_names = [font]
        else:
            font_names = list(font)

        cfg_font = Config.get.font
        if isinstance(cfg_font, str):
            font_names.append(cfg_font)
        else:
            font_names.extend(cfg_font)

        fonts = [
            Font.get_by_info(get_font_info_by_attrs(name, weight, style, force_full_name))
            for name in font_names
        ]

        if format != Text.Format.RichText:
            self.text = text
        else:
            self.text, tag_queue = extract_tag_queue(text)

        params = _TextParams(fonts, font_size, render == Text.Render.PixelText)

        super().__init__(
            *[TextLine(line_text, params, **line_kwargs) for line_text in self.text.split('\n')],
            stroke_alpha=stroke_alpha,
            fill_alpha=fill_alpha,
            stroke_background=stroke_background,
            **kwargs,
        )

        if format == Text.Format.RichText:
            self.apply_rich_text(tag_queue)  # type: ignore

        for line in self:
            line.arrange_in_line()
        self.arrange_in_lines()

        if center:
            self.points.to_center()

    def is_null(self) -> bool:
        return True

    def idx_to_row_col(self, idx: int) -> tuple[int, int]:
        """
        由字符索引得到 行数、列数 索引
        """
        idx = max(0, idx)
        for i, line in enumerate(self):
            if idx < len(line):
                return i, idx
            idx -= len(line)
        return len(self) - 1, len(line)

    def select_parts(self, pattern: str | re.Pattern, group: int = 0):
        """
        根据 ``pattern`` **正则表达式** 获得文字中的部分

        :param pattern: 用于匹配的正则表达式

        :param group: 对于正则表达式，指定使用第几个分组进行匹配，默认 ``0`` 表示整个匹配片段，其余数字表示对应的分组

        提示：如果不希望使用正则表达式，可以使用 ``re.escape`` 进行转义，例如 ``re.escape('a[i]')`` 来正确匹配字符串中的 ``a[i]``

        示例：

        .. code-block:: python

            txt = Text('Hello World!')
            txt.select_parts('World').set(color=RED)

        上面这个示例会选取出 ``Hello World!`` 中的 ``World`` 部分，并将其颜色设置为红色

        .. code-block:: python

            txt = Text('for i in range(100) if i % 3 == 0 or i % 5 == 0')
            txt.select_parts(r'[^f](or)', 1).set(color=BLUE)

        上面这个示例会选取出其中的 ``or`` 部分，并且避免选取 ``for`` 中的 ``or``
        """
        total_text: str = ''.join([line.text for line in self])
        parts = []
        for mch in re.finditer(pattern, total_text):
            l_row, l_col = self.idx_to_row_col(mch.start(group))
            r_row, r_col = self.idx_to_row_col(mch.end(group))
            if l_row == r_row:
                parts.append(self[l_row][l_col:r_col])
            else:
                parts.append(
                    Group(
                        *it.chain(
                            self[l_row][l_col:],
                            *self[l_row + 1 : r_row],
                            self[r_row][:r_col],
                        )
                    )
                )
        return Group(*parts)

    def arrange_in_lines(self, buff: float = 0, base_buff: float = 0.85) -> Self:
        """
        :param buff: 每行之间的额外间距
        :param base_buff: 每行之间的基本间距，默认值 ``0.85`` 用于将两行上下排列，如果是 ``0`` 则会让两行完全重合，大部分时候不需要传入该值
        """
        if not self.has_child():
            return self

        pos = self[0].get_mark_orig()
        for line in self[1:]:
            vert = line.get_mark_orig() - line.get_mark_up()
            target = pos + base_buff * vert + buff * normalize(vert)
            line.points.shift(target - line.get_mark_orig())
            pos = line.get_mark_orig()

        return self

    def match_to(self, target: Text | TextLine, *, self_lineno: int = 0) -> Self:
        """
        将该文本与目标文本或文本行对齐

        :param target: 目标文本或文本行
        :param self_lineno: 将自身的哪一行与目标对齐，默认为首行（即 ``self_lineno=0``）
        """
        line = target if isinstance(target, TextLine) else target[0]
        TextLine._match_to(self, self[self_lineno], line)
        return self

    def apply_rich_text(self, tag_queue: TagQueue) -> None:
        """
        应用富文本效果
        """
        text_at = 0
        for line in self:
            for char in line:
                tag_queue.advance_to(text_at)
                tag_queue.apply_to(char)
                text_at += 1
            text_at += 1  # 因为 TagQueue 的索引是考虑换行的，所以这里换行处也要 +1

        tag_queue.advance_to(text_at)  # 清理最后的富文本标签，避免忽略可能出现的警告


class Title(Group):
    """
    标题

    - ``include_underline=True`` 会添加下划线（默认添加）
    - ``underline_width`` 下划线的长度（默认 ``屏幕宽 - 2个单位``）
    - ``match_underline_width_to_text=True`` 时将下划线的长度和文字匹配（默认为 ``False``）
    """

    def __init__(
        self,
        text: str,
        font: str | Iterable[str] = [],
        font_size: float = DEFAULT_FONT_SIZE,
        include_underline: bool = True,
        underline_width: float | None = None,
        underline_buff: float = MED_SMALL_BUFF,
        match_underline_width_to_text: bool = False,
        depth: float | None = None,
        **kwargs,
    ):
        txt = Text(text, font=font, font_size=font_size, **kwargs)
        txt.points.to_border(UP)

        super().__init__(txt)
        self.txt = txt

        if include_underline:
            if underline_width is None and not match_underline_width_to_text:
                underline_width = Config.get.frame_width - 2

            underline = Line(LEFT, RIGHT)
            underline.points.next_to(txt, DOWN, buff=underline_buff)
            if match_underline_width_to_text:
                underline.points.set_width(txt.points.box.width)
            else:
                underline.points.set_width(underline_width)

            self.add(underline)
            self.underline = underline

        if depth is not None:
            self.depth.set(depth)


class SourceDisplayer(Text):
    """
    显示 ``obj`` 的源代码
    """

    def __init__(
        self,
        obj,
        font_size=12,
        color=GREY,
        render: Text.Render | Literal['vitem', 'pixel'] = 'pixel',
        **kwargs,
    ):
        super().__init__(
            inspect.getsource(obj), font_size=font_size, color=color, render=render, **kwargs
        )
        self.points.to_border(UL)
