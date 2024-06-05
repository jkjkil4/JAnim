from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Generator

import freetype as FT
import numpy as np
from fontTools.ttLib import TTCollection, TTFont, TTLibError

from janim.exception import FontNotFoundError
from janim.utils.bezier import PathBuilder
from janim.logger import log
from janim.locale.i18n import get_local_strings

if TYPE_CHECKING:
    from fontTools.ttLib.tables._n_a_m_e import table__n_a_m_e

_ = get_local_strings('font')


@dataclass
class FontInfo:
    filepath: str
    index: int
    name: str
    table: table__n_a_m_e


_font_finder: Generator[FontInfo, None, None] | None = None
_found_infos: dict[str, FontInfo] = {}


def _font_finder_func() -> Generator[FontInfo, None, None]:
    from janim.utils.font_manager import findSystemFonts
    for filepath in findSystemFonts():
        try:
            fonts = TTCollection(filepath).fonts    \
                if filepath.endswith('ttc')         \
                else [TTFont(filepath)]
        except TTLibError:
            # i18n?
            log.debug(f'Skipped font "{filepath}"')
            continue

        for i, font in enumerate(fonts):
            table: table__n_a_m_e = font['name']
            name = table.getDebugName(4) or ''
            info = FontInfo(filepath, i, name, table)
            _found_infos[name] = info
            yield info


def _get_font_finder() -> Generator[FontInfo, None, None]:
    global _font_finder
    if _font_finder is None:
        _font_finder = _font_finder_func()
    return _font_finder


def get_font_info_by_name(font_name: str) -> FontInfo:
    '''
    通过字体名得到字体文件信息

    例：通过 ``Consolas`` 得到 ``FontInfo('C:\\Windows\\Fonts\\consola.ttf', 0, 'Consolas', <'name' table at ...>)``
    '''
    info = _found_infos.get(font_name, None)
    if info is not None:
        return info

    finder = _get_font_finder()

    try:
        while True:
            info = next(finder)
            if info.name == font_name:
                return info
    except StopIteration:
        raise FontNotFoundError(
            _('No font named "{font_name}"')
            .format(font_name=font_name)
        )


def get_found_infos() -> dict[str, FontInfo]:
    finder = _get_font_finder()
    try:
        while True:
            next(finder)
    except StopIteration:
        pass

    return _found_infos


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
        self.face.set_char_size(48 << 6)
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
