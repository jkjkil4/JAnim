from __future__ import annotations
from typing import Optional
from janim.typing import Self

from janim.items.geometry.line import Line
from janim.items.vitem import VGroup
from janim.utils.bezier import outer_interpolate
from janim.constants import *

class NumberLine(Line):
    def __init__(
        self,
        x_range = [-8, 8, 1],
        *,
        unit_size: float = 1,
        color: JAnimColor = GREY_B,
        stroke_width: float = 0.02,
        width: Optional[float] = None,
        include_tip: bool = False,                      # 是否显示箭头
        include_ticks: bool = True,                     # 是否显示刻度
        tick_size: float = 0.1,                         # 刻度大小
        longer_tick_multiple: float = 1.5,              # 长刻度大小倍数
        numbers_with_elongated_ticks: Iterable = [],    # 指定哪些数字是长刻度
        include_numbers: bool = False,                  # 是否显示数字
        numbers_to_exclude: Optional[Iterable] = None   # 需要排除的数字
    ) -> None:
        if len(x_range) == 2:
            x_range = [*x_range, 1]
        self.x_min, self.x_max, self.x_step = x_range

        self.unit_size = unit_size
        self.tick_size = tick_size
        self.longer_tick_multiple = longer_tick_multiple
        self.numbers_with_elongated_ticks = numbers_with_elongated_ticks

        super().__init__(
            self.x_min * RIGHT, self.x_max * RIGHT,
            color=color,
            stroke_width=stroke_width
        )

        if width:
            self.set_width(width)
            self.unit_size = self.get_unit_size()
        else:
            self.scale(self.unit_size)
        self.to_center()

        if include_tip:
            self.add_tip()
        if include_ticks:
            self.add_ticks()
        if include_numbers:
            self.add_numbers(excluding=numbers_to_exclude)

    def get_unit_size(self) -> float:
        return self.get_length() / (self.x_max - self.x_min)
    
    def number_to_point(self, number: float | np.ndarray) -> np.ndarray:
        alpha = (number - self.x_min) / (self.x_max - self.x_min)
        return outer_interpolate(self.get_start(), self.get_end(), alpha)
    
    def get_tick_range(self) -> np.ndarray:
        x_min_tmp = self.x_min // self.unit_size
        if abs(x_min_tmp % 1) >= DEFAULT_EPS:
            x_min_tmp += 1
        x_min = self.unit_size * x_min_tmp
        x_max = self.unit_size * (self.x_max // self.unit_size + 0.5)
        r = np.arange(x_min, x_max, self.x_step)
        return r
    
    def add_ticks(self):
        ticks = VGroup()
        for x in self.get_tick_range():
            size = self.tick_size
            if np.isclose(self.numbers_with_elongated_ticks, x).any():
                size *= self.longer_tick_multiple
            ticks.add(self.get_tick(x, size))
        self.add(ticks)
        self.ticks = ticks

    def get_tick(self, x: float, size: Optional[float] = None) -> Line:
        if size is None:
            size = self.tick_size
        result = Line(size * DOWN, size * UP)
        result.rotate(self.get_angle())
        result.move_to(self.number_to_point(x))
        result.set_color(self.get_rgbas()[0][:3])
        return result

    def add_numbers(self):
        pass # TODO: add_numbers

