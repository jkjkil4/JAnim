from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

import freetype as FT
import numpy as np
from fontTools.ttLib import TTCollection, TTFont, TTLibError

from janim.constants import FRAME_PPI
from janim.exception import FontNotFoundError
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.utils.bezier import PathBuilder
from janim.utils.font.exception import EXCEPTION_MAP
from janim.utils.font.variant import (WEIGHT_MAP, Style, StyleName, Weight,
                                      WeightName)

if TYPE_CHECKING:
    from fontTools.ttLib.tables._n_a_m_e import table__n_a_m_e
    from fontTools.ttLib.tables.O_S_2f_2 import table_O_S_2f_2

_ = get_local_strings('database')


@dataclass
class FontDatabase:
    family_by_name: defaultdict[str, FontFamily]
    font_by_full_name: dict[str, FontInfo]


class FontFamily:
    def __init__(self):
        self.infos: list[FontInfo] = []

    def add(self, info: FontInfo) -> None:
        self.infos.append(info)

    def find_best_variant(self, weight: int | Weight, style: Style) -> FontInfo:
        if len(self.infos) == 1:
            return self.infos[0]

        if not isinstance(weight, int):
            weight = WEIGHT_MAP[weight]

        for i, info in enumerate(self.infos):
            key = (
                self.style_distance(info.style, style),
                abs(info.weight - weight),
                -info.weight
            )
            if i == 0 or key < best_key:
                best = info
                best_key = key  # noqa: F841

        return best

    @staticmethod
    def style_distance(s1: Style, s2: Style) -> int:
        if s1 == s2:
            return 0
        if s1 != Style.Normal and s2 != Style.Normal:
            return 1
        return 2


class FontInfo:
    def __init__(self, filepath: str, font: TTFont, index: int):
        self.filepath = filepath
        self.index = index

        self.name: table__n_a_m_e = font['name']
        self.os2: table_O_S_2f_2 = font.get('OS/2', None)

        self.exception = EXCEPTION_MAP.get(self.postscript_name, None)

    @property
    def family_name(self) -> str:
        return self.name.getBestFamilyName()

    @property
    def full_name(self) -> str:
        return self.name.getBestFullName()

    @property
    def postscript_name(self) -> str:
        return self.name.getDebugName(6)

    @property
    def weight(self) -> int:
        if self.exception is not None and self.exception.weight is not None:
            return self.exception.weight
        if self.os2 is None:
            return 400
        return self.os2.usWeightClass

    @property
    def style(self) -> Style:
        if self.exception is not None and self.exception.style is not None:
            return self.exception.style
        if self.os2 is None:
            return Style.Normal

        fs_selection = self.os2.fsSelection
        if fs_selection & 0x01:
            return Style.Italic
        if fs_selection & 0x200:
            return Style.Oblique

        return Style.Normal


_database: FontDatabase | None = None


def get_database() -> FontDatabase:
    global _database

    if _database is not None:
        return _database

    from janim.utils.font_manager import findSystemFonts

    family_by_name = defaultdict(FontFamily)
    font_by_full_name = {}

    for filepath in findSystemFonts():
        try:
            fonts = TTCollection(filepath, lazy=True).fonts \
                if filepath.endswith('ttc')                 \
                else [TTFont(filepath, lazy=True)]
        except TTLibError:
            log.debug(_('Skipped font "{filepath}"').format(filepath=filepath))
            continue

        for i, font in enumerate(fonts):
            info = FontInfo(filepath, font, i)
            family_by_name[info.family_name].add(info)
            font_by_full_name[info.full_name] = info

    _database = FontDatabase(family_by_name, font_by_full_name)
    return _database


def get_font_info_by_attrs(
    name: str,
    weight: int | Weight | WeightName,
    style: Style | StyleName,
    force_full_name: bool = False
) -> FontInfo:
    db = get_database()

    # e.g. ('LXGW WenKai Lite', 'medium', 'normal')
    if not force_full_name:
        family = db.family_by_name.get(name, None)
        if family is not None:
            return family.find_best_variant(weight, style)

    # e.g. 'LXGW WenKai Lite Medium'
    info = db.font_by_full_name.get(name, None)
    if info is not None:
        return info

    # deprecated
    for full_name, info in db.font_by_full_name.items():
        if info.name.getDebugName(4) == name:
            log.warning(
                _('font="{deprecated}" is deprecated and will no longer be available in JAnim 3.3, '
                  'use font="{full_name}" instead')
                .format(deprecated=name, full_name=full_name)
            )
            return info

    raise FontNotFoundError(
        _('No font named "{font_name}"')
        .format(font_name=name)
    )


class Font:
    filepath_to_font_map: dict[tuple[str, int], Font] = {}

    @staticmethod
    def get(filepath: str) -> Font:
        key = (filepath, 0)
        cache = Font.filepath_to_font_map.get(key)
        if cache is not None:
            return cache

        font = Font(filepath)
        Font.filepath_to_font_map[key] = font
        return font

    @staticmethod
    def get_by_info(info: FontInfo) -> Font:
        key = (info.filepath, info.index)
        cache = Font.filepath_to_font_map.get(key)
        if cache is not None:
            return cache

        font = Font(info.filepath, info.index)
        Font.filepath_to_font_map[key] = font
        return font

    def __init__(self, filepath: str | FontInfo, index: int = 0) -> None:
        self.filepath = filepath
        with open(filepath, 'rb') as file:
            self.face = FT.Face(file, index=index)

        self.face.select_charmap(FT.FT_ENCODING_UNICODE)

        # 将字号为 48 的字形作为读取的基准
        # 这里使用 48 << 6 是因为 freetype 里的点数是用 26.6 数值格式存储的，所以需要 << 6 空出 6 个小数位
        # （26.6 数值格式也可以理解成单位为 1/64 点）
        # 这里我们使用的 dpi/ppi 为 FRAME_PPI（默认为 144）
        self.face.set_char_size(48 << 6, 0, FRAME_PPI, FRAME_PPI)

        self.cached_glyph: dict[int, Font.GlyphData] = {}

    @dataclass
    class GlyphData:
        array: np.ndarray
        advance: tuple[int, int]

    def get_glyph_data(self, char: str) -> tuple[np.ndarray, tuple[int, int]]:
        value = ord(char)
        cached = self.cached_glyph.get(value, None)
        if cached is not None:
            return cached.array, cached.advance

        # 读取字符
        self.face.load_char(value, FT.FT_LOAD_DEFAULT | FT.FT_LOAD_NO_BITMAP)
        glyph: FT.Glyph = self.face.glyph
        outline: FT.Outline = glyph.outline

        builder: PathBuilder = PathBuilder()

        def wrap_points(func: Callable) -> Callable:
            def wrapper(*args) -> None:
                func(*[np.array([p.x, p.y, 0]) for p in args[:-1]])
            return wrapper

        # 解析轮廓
        outline.decompose(
            outline,
            wrap_points(builder.move_to),
            wrap_points(builder.line_to),
            wrap_points(builder.conic_to),
            wrap_points(builder.cubic_to)
        )

        data = Font.GlyphData(builder.get(), (glyph.advance.x, glyph.advance.y))
        data.array.setflags(write=False)
        self.cached_glyph[value] = data

        return data.array, data.advance
