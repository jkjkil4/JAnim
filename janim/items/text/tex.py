from __future__ import annotations
from typing import Optional

from janim.constants import *
from janim.items.svg_item import SVGItem
from janim.items.text.text import get_stroke_width_by_font_size
from janim.utils.tex_file_writing import (
    tex_to_svg_file,
    display_during_execution,
    get_tex_conf
)

SCALE_FACTOR_PER_FONT_POINT = 0.001

DEFAULT_TEXDOC_FONT_SIZE = 36

class TexDoc(SVGItem):
    def __init__(
        self,
        tex_string: str,
        width: Optional[float] = None,
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
        font_size: float = DEFAULT_TEXDOC_FONT_SIZE,
        **kwargs
    ) -> None:
        assert isinstance(tex_string, str)
        self.tex_string = tex_string
        self.font_size = font_size

        if stroke_width is None:
            stroke_width = get_stroke_width_by_font_size(font_size)

        super().__init__(
            width=width,
            height=height,
            fill_opacity=fill_opacity,
            stroke_width=stroke_width,
            svg_default=svg_default,
            path_string_config=path_string_config,
            **kwargs
        )

        if width is None and height is None:
            self.scale(SCALE_FACTOR_PER_FONT_POINT * self.font_size, about_point=ORIGIN)

    def move_into_position(self) -> None:
        self.move_anchor_to(ORIGIN)

    @property
    def hash_seed(self) -> tuple:
        return (
            self.__class__.__name__,
            self.svg_default,
            self.path_string_config,
            self.tex_string
        )
    
    def get_execution_message_body(self) -> str:
        return 'tex document'
    
    def get_file_path(self) -> str:
        with display_during_execution(f'Writing {self.get_execution_message_body()}'):
            file_path = tex_to_svg_file(self.tex_string)
        return file_path
    

class Tex(TexDoc):
    def __init__(
        self,
        tex_string: str,
        pkg_string: str = '',
        math_mode: bool = True,
        alignment: str = '\\centering',
        **kwargs
    ) -> None:
        tex_string = tex_string.strip()
        self.orig_tex_string = tex_string
        self.pkg_string = pkg_string
        self.math_mode = math_mode
        self.alignment = alignment

        if math_mode:
            tex_string = '\\begin{align*}\n' + tex_string + '\n\\end{align*}'
        
        tex_string = alignment + '\n' + tex_string

        conf = get_tex_conf()

        super().__init__(
            conf['tex_body']
                .replace(conf['text_to_replace'], tex_string)
                .replace(conf['pkg_to_replace'], pkg_string), 
            **kwargs
        )

    @property
    def hash_seed(self) -> tuple:
        return (
            self.__class__.__name__,
            self.svg_default,
            self.path_string_config,
            self.orig_tex_string,
            self.math_mode,
            self.alignment
        )
    
    def get_execution_message_body(self) -> str:
        return f'"{self.orig_tex_string}"'
    
    def move_into_position(self) -> None:
        return self.to_center()
    
class TexText(Tex):
    def __init__(
        self,
        tex_string: str,
        pkg_string: str = '',
        math_mode: bool = False,
        **kwargs
    ) -> None:
        super().__init__(tex_string, pkg_string, math_mode, **kwargs)

