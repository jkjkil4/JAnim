from __future__ import annotations

from typing import Callable, Optional, TypeVar, Type

import numpy as np
from janim.constants import np
from janim.typing import Self

from janim.constants import *
from janim.items.vitem import VItem
from janim.items.text.tex import Tex
from janim.items.text.text import Text

T = TypeVar('T', bound=VItem)

# TODO: optimize
class DecimalNumber(VItem):
    def __init__(
        self,
        number: float | complex = 0,
        *,
        num_decimal_places: int = 2,
        include_sign: bool = False,
        group_with_commas: bool = True,
        digit_buff_per_font_unit: float = 0.001,
        show_ellipsis: bool = False,
        unit: str = None,   # Aligned to bottom unless it starts with "^"
        edge_to_fix: np.ndarray = LEFT,
        font_size: float = 48,
        text_config: dict = dict(), # Do not pass in font_size here
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.num_decimal_places = num_decimal_places
        self.include_sign = include_sign
        self.group_with_commas = group_with_commas
        self.digit_buff_per_font_unit = digit_buff_per_font_unit
        self.show_ellipsis = show_ellipsis
        self.unit = unit
        self.edge_to_fix = edge_to_fix
        self.font_size = font_size
        self.text_config = text_config

        self.set_subitems_from_number(number)

    def set_subitems_from_number(self, number: float | complex) -> Self:
        self.number = number
        self.set_subitems([])
        string_to_item_ = lambda s: self.string_to_item(s, **self.text_config)
        num_string = self.get_num_string(number)
        self.add(*map(string_to_item_, num_string))

        # Add non_numerical bits
        if self.show_ellipsis:
            dots = string_to_item_('...')
            dots.arrange(RIGHT, buff=2 * dots[0].get_width())
            self.add(dots)
        if self.unit is not None:
            self.unit_sign = self.string_to_item(self.uint, Tex)
            self.add(self.unit_sign)
        
        self.arrange(
            buff=self.digit_buff_per_font_unit * self.get_font_size(),
            aligned_edge=DOWN
        )

        # Handle alignment of parts that should be aligned
        # to the bottom
        for i, c in enumerate(num_string):
            if c == "–" and len(num_string) > i + 1:
                self[i].align_to(self[i + 1], UP)
                self[i].shift(self[i + 1].get_height() * DOWN / 2)
            elif c == ",":
                self[i].shift(self[i].get_height() * DOWN / 2)
        if self.unit and self.unit.startswith("^"):
            self.unit_sign.align_to(self, UP)

        return self
    
    def get_num_string(self, number: float | complex) -> str:
        if isinstance(number, complex):
            formatter = self.get_complex_formatter()
        else:
            formatter = self.get_formatter()
        num_string = formatter.format(number)

        rounded_num = np.round(number, self.num_decimal_places)
        if num_string.startswith("-") and rounded_num == 0:
            if self.include_sign:
                num_string = "+" + num_string[1:]
            else:
                num_string = num_string[1:]
        num_string = num_string.replace("-", "–")
        return num_string

    def get_num_string(self, number: float | complex) -> str:
        if isinstance(number, complex):
            formatter = self.get_complex_formatter()
        else:
            formatter = self.get_formatter()
        num_string = formatter.format(number)

        rounded_num = np.round(number, self.num_decimal_places)
        if num_string.startswith("-") and rounded_num == 0:
            if self.include_sign:
                num_string = "+" + num_string[1:]
            else:
                num_string = num_string[1:]
        num_string = num_string.replace("-", "–")
        return num_string

    def get_font_size(self) -> float:
        return self.font_size

    def string_to_item(self, string: str, item_class: Type[T] = Text, **kwargs) -> T:
        item = item_class(string, font_size=1, **kwargs)
        item.scale(self.get_font_size())
        return item

    def get_formatter(self, **kwargs) -> str:
        """
        Configuration is based first off instance attributes,
        but overwritten by any kew word argument.  Relevant
        key words:
        - include_sign
        - group_with_commas
        - num_decimal_places
        - field_name (e.g. 0 or 0.real)
        """
        config = dict([
            (attr, getattr(self, attr))
            for attr in [
                "include_sign",
                "group_with_commas",
                "num_decimal_places",
            ]
        ])
        config.update(kwargs)
        return "".join([
            "{",
            config.get("field_name", ""),
            ":",
            "+" if config["include_sign"] else "",
            "," if config["group_with_commas"] else "",
            ".", str(config["num_decimal_places"]), "f",
            "}",
        ])

    def get_complex_formatter(self, **kwargs) -> str:
        return "".join([
            self.get_formatter(field_name="0.real"),
            self.get_formatter(field_name="0.imag", include_sign=True),
            "i"
        ])

    def set_value(self, number: float | complex):
        move_to_point = self.get_bbox_point(self.edge_to_fix)
        old_subitems = list(self.items)
        self.set_subitems_from_number(number)
        self.move_to(move_to_point, self.edge_to_fix)
        for sm1, sm2 in zip(self.items, old_subitems):
            sm1.match_style(sm2)
        return self

    def get_value(self) -> float | complex:
        return self.number

    def increment_value(self, delta_t: float | complex = 1) -> None:
        self.set_value(self.get_value() + delta_t)

class Integer(DecimalNumber):
    def __init__(
        self,
        number: float | complex = 0,
        num_decimal_places: int = 0,
        **kwargs
    ) -> None:
        super().__init__(number, num_decimal_places=num_decimal_places, **kwargs)

    def get_value(self) -> int:
        return int(np.round(super().get_value()))
