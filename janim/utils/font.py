from __future__ import annotations

from typing import Callable
from functools import lru_cache

import freetype as FT
import numpy as np
from fontTools.ttLib import TTCollection, TTFont

from janim.utils.bezier import PathBuilder

fontpaths: list[str] = None


@lru_cache()
def get_fontpath_by_name(font_name: str) -> str:
    '''
    通过字体名得到字体文件路径

    例：通过 `Consolas` 得到 `C:\\Windows\\Fonts\\consola.ttf`
    '''
    global fontpaths

    if fontpaths is None:
        from janim.utils.font_manager import findSystemFonts
        fontpaths = findSystemFonts()

    for filepath in fontpaths:
        fonts = TTCollection(filepath).fonts    \
            if filepath[-3:].endswith('ttc')    \
            else [TTFont(filepath)]

        for font in fonts:
            if font['name'].getDebugName(4) == font_name:
                return filepath

    raise ValueError(f'No font named "{font_name}"')


class Font:
    filepath_to_font_map: dict[str, Font] = {}

    @staticmethod
    def get(filepath: str) -> FT.Face:
        if filepath in Font.filepath_to_font_map:
            return Font.filepath_to_font_map[filepath]

        font = Font(filepath)
        Font.filepath_to_font_map[filepath] = font
        return font

    def __init__(self, filepath: str) -> None:
        self.face = FT.Face(filepath)
        self.face.select_charmap(FT.FT_ENCODING_UNICODE)
        self.face.set_char_size(48 << 6)

    def get_glyph_data(self, char: str) -> tuple[np.ndarray, tuple[int, int]]:
        # 读取字符
        self.face.load_char(char, FT.FT_LOAD_DEFAULT | FT.FT_LOAD_NO_BITMAP)
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

        return builder.get()[::-1], (glyph.advance.x, glyph.advance.y)
