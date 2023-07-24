from __future__ import annotations
from typing import Tuple

from fontTools.ttLib import TTFont, TTCollection
import freetype as FT
from functools import lru_cache
import numpy as np

from janim.constants import *
from janim.utils.space_ops import midpoint
from janim.items.vitem import VItem


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
        
        points = []
        end_point = ORIGIN

        def f(p) -> np.ndarray:
            return np.array([p.x, p.y, 0])
        
        def move_to(v_point, _):
            nonlocal end_point
            end_point = f(v_point)

        def line_to(v_point, _):
            nonlocal end_point
            point = f(v_point)
            points.extend([end_point, midpoint(end_point, point), point])
            end_point = point

        def conic_to(v_handle, v_point, _):
            nonlocal end_point
            handle = f(v_handle)
            point = f(v_point)

            if np.all(end_point == handle):
                line_to(v_point, _)
                return
            
            points.extend([end_point, handle, point])
            end_point = point

        def cubic_to(v_handle1, v_handle2, v_point, _):
            raise NotImplementedError('Cubic curve is not supported')
        
        # 解析轮廓
        outline.decompose(outline, move_to, line_to, conic_to, cubic_to)
        if len(points) // 3 > 0:
            points = VItem.subdivide_sharp_curves_from_points(points)

        return points, (glyph.advance.x, glyph.advance.y)



