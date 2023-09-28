from __future__ import annotations
from janim.typing import Self

from janim.items.geometry.line import Line
from janim.items.vitem import VGroup
from janim.items.numbers import DecimalNumber
from janim.utils.bezier import outer_interpolate, interpolate
from janim.utils.dict_ops import merge_dicts_recursively
from janim.utils.simple_functions import fdiv
from janim.constants import *

class NumberLine(Line):
    tip_config_d= dict(
        back_width=0.25,
        body_length=0.25
    )
    decimal_number_config_d = dict(
        num_decimal_places=0,
        font_size=36
    )

    def __init__(
        self,
        x_range = [-8, 8, 1],
        *,
        unit_size: int = 1,
        color: JAnimColor = GREY_B,
        stroke_width: float = 0.02,
        width: float | None = None,
        include_tip: bool = False,                      # 是否显示箭头
        tip_config: dict = {},                          # 箭头属性
        include_ticks: bool = True,                     # 是否显示刻度
        tick_size: float = 0.1,                         # 刻度大小
        longer_tick_multiple: float = 1.5,              # 长刻度大小倍数
        numbers_with_elongated_ticks: Iterable = [],    # 指定哪些数字是长刻度
        include_numbers: bool = False,                  # 是否显示数字
        numbers_to_exclude: Iterable | None = None,     # 需要排除的数字
        line_to_number_direction: np.ndarray = DOWN,    # 详见 get_number_item
        line_to_number_buff: float = MED_SMALL_BUFF,    # 详见 get_number_item
        decimal_number_config: dict = {},               # 数字属性
    ) -> None:
        if len(x_range) == 2:
            x_range = [*x_range, 1]
        self.x_min, self.x_max, self.x_step = x_range

        self.unit_size = unit_size
        self.tip_config = merge_dicts_recursively(
            self.tip_config_d, 
            tip_config
        )
        self.tick_size = tick_size
        self.longer_tick_multiple = longer_tick_multiple
        self.numbers_with_elongated_ticks = numbers_with_elongated_ticks
        self.numbers_to_exclude = numbers_to_exclude
        self.line_to_number_direction = line_to_number_direction
        self.line_to_number_buff = line_to_number_buff
        self.decimal_number_config = merge_dicts_recursively(
            self.decimal_number_config_d,
            decimal_number_config
        )

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
            self.add_numbers()

    def get_unit_size(self) -> float:
        return self.get_length() / (self.x_max - self.x_min)
    
    def number_to_point(self, number: float | np.ndarray) -> np.ndarray:
        alpha = (number - self.x_min) / (self.x_max - self.x_min)
        return outer_interpolate(self.get_start(), self.get_end(), alpha)
    
    def get_tick_range(self) -> np.ndarray:
        tmp = self.x_min // self.x_step
        mod = self.x_min % self.x_step
        if mod >= DEFAULT_EPS:
            tmp += 1
        x_min = self.x_step * tmp

        tmp = self.x_max // self.x_step
        mod = self.x_max % self.x_step
        if self.x_step - mod < DEFAULT_EPS:
            tmp += 1.5
        else:
            tmp += 0.5
        x_max = self.x_step * tmp

        r = np.arange(x_min, x_max, self.x_step)
        return r
    
    def add_ticks(
        self,
        excluding: Iterable[float] | None = None,
    ) -> None:
        if excluding is None:
            excluding = self.numbers_to_exclude

        ticks = VGroup()
        for x in self.get_tick_range():
            if excluding is not None and np.isclose(excluding, x).any():
                continue
            
            size = self.tick_size
            if np.isclose(self.numbers_with_elongated_ticks, x).any():
                size *= self.longer_tick_multiple
            ticks.add(self.get_tick(x, size))
        self.add(ticks)
        self.ticks = ticks

    def get_tick(self, x: float, size: float | None = None) -> Line:
        if size is None:
            size = self.tick_size
        result = Line(size * DOWN, size * UP)
        result.rotate(self.get_angle())
        result.move_to(self.number_to_point(x))
        result.set_color(self.get_rgbas()[0][:3])
        return result

    def add_numbers(
        self,
        x_values: Iterable[float] | None = None,
        excluding: Iterable[float] | None = None,
        font_size: int = 24,
        **kwargs
    ) -> VGroup:
        if x_values is None:
            x_values = self.get_tick_range()
        
        kwargs['font_size'] = font_size

        if excluding is None:
            excluding = self.numbers_to_exclude
        
        numbers = VGroup()
        for x in x_values:
            if excluding is not None and np.isclose(excluding, x).any():
                continue
            numbers.add(self.get_number_item(x, **kwargs))
        self.add(numbers)
        self.numbers = numbers
        return numbers

    def get_number_item(
        self,
        x: float,
        direction: np.ndarray | None = None,
        buff: float | None = None,
        **number_config 
    ) -> DecimalNumber:
        number_config = merge_dicts_recursively(
            self.decimal_number_config, number_config
        )
        if direction is None:
            direction = self.line_to_number_direction
        if buff is None:
            buff = self.line_to_number_buff

        num_item = DecimalNumber(x, **number_config)
        num_item.next_to(
            self.number_to_point(x),
            direction=direction,
            buff=buff
        )
        if x < 0 and direction[0] == 0:
            num_item.shift(num_item[0].get_width() * LEFT / 2)
        return num_item
    
    def number_to_point(self, number: float | np.ndarray) -> np.ndarray:
        alpha = (number - self.x_min) / (self.x_max - self.x_min)
        return outer_interpolate(self.get_start(), self.get_end(), alpha)
    
    def point_to_number(self, point: np.ndarray) -> float:
        points = self.get_points()
        start = points[0]
        end = points[-1]
        vect = end - start
        proportion = fdiv(
            np.dot(point - start, vect),
            np.dot(end - start, vect),
        )
        return interpolate(self.x_min, self.x_max, proportion)

    def n2p(self, number: float) -> np.ndarray:
        """Abbreviation for number_to_point"""
        return self.number_to_point(number)

    def p2n(self, point: np.ndarray) -> float:
        """Abbreviation for point_to_number"""
        return self.point_to_number(point)

class UnitInterval(NumberLine):
    def __init__(
        self,
        x_range = [0, 1, 0.1],
        *,
        unit_size: int = 10,
        numbers_with_elongated_ticks: Iterable = [0, 1],
        decimal_number_config: dict = dict(
            num_decimal_places=1
        ),
        **kwargs
    ) -> None:
        super().__init__(
            x_range, 
            unit_size=unit_size, 
            numbers_with_elongated_ticks=numbers_with_elongated_ticks,
            decimal_number_config=decimal_number_config,
            **kwargs
        )

