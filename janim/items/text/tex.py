from __future__ import annotations
from typing import Optional

from janim.constants import *
from janim.items.svg_item import SVGItem
from janim.items.text.text import DEFAULT_FONT_SIZE, get_stroke_width_by_font_size
from janim.utils.tex_file_writing import (
    tex_to_svg_file,
    display_during_execution
)

SCALE_FACTOR_PER_FONT_POINT = 0.001

class Tex(SVGItem):
    def __init__(
        self,
        tex_string: str,
        height: Optional[float] = None,
        fill_opacity: float = 1.0,
        stroke_width: Optional[float] = None,
        svg_default: dict = {
            'color': WHITE,
            'fill_color': WHITE
        },
        path_string_config: dict = {
            'should_subdivide_sharp_curves': True,
            'should_remove_null_curves': True
        },
        font_size: float = DEFAULT_FONT_SIZE,
        **kwargs
    ) -> None:
        assert isinstance(tex_string, str)
        self.tex_string = tex_string
        self.font_size = font_size

        if stroke_width is None:
            stroke_width = get_stroke_width_by_font_size(font_size)

        super().__init__(
            height=height,
            fill_opacity=fill_opacity,
            stroke_width=stroke_width,
            svg_default=svg_default,
            path_string_config=path_string_config,
            **kwargs
        )
        
        if height is None:
            self.scale(SCALE_FACTOR_PER_FONT_POINT * self.font_size)

    @property
    def hash_seed(self) -> tuple:
        return (
            self.__class__.__name__,
            self.svg_default,
            self.path_string_config,
            self.tex_string,
            # self.alignment,
            # self.math_mode
        )
    
    def get_file_path(self) -> str:
        with display_during_execution(f'Writing "{self.tex_string}"'):
            file_path = tex_to_svg_file(self.tex_string)
        return file_path
    

