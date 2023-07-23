from __future__ import annotations
from typing import Tuple

import matplotlib.font_manager as fm
from fontTools.ttLib import TTFont, TTCollection
from functools import lru_cache
import freetype as FT

fontpaths: list[str] = None

@lru_cache()
def get_fontpath_by_name(font_name: str) -> str:
    '''
    通过字体名得到字体文件路径

    例：通过 `Consolas` 得到 `C:\\Windows\\Fonts\\consola.ttf`
    '''
    global fontpaths

    if fontpaths is None:
        fontpaths = fm.findSystemFonts()

    for filepath in fontpaths:
        fonts = TTCollection(filepath).fonts    \
            if filepath[-3:].endswith('ttc')    \
            else [TTFont(filepath)]

        for font in fonts:
            if font['name'].getDebugName(4) == font_name:
                return filepath

    raise ValueError(f'No font named "{font_name}"')

filepath_to_fontface_map = {}

def get_font_face(filepath: str) -> FT.Face:
    if filepath in filepath_to_fontface_map:
        return filepath_to_fontface_map[filepath]
    
    face = FT.Face(filepath)
    face.select_charmap(FT.FT_ENCODING_UNICODE)
    face.set_char_size(48 << 6)
    filepath_to_fontface_map[filepath] = face
    return face

