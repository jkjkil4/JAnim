
from typing import Iterable

import numpy as np

from janim.constants import DOWN, GREY_B, LEFT, MED_SMALL_BUFF, RIGHT, UP
from janim.items.geometry.arrow import ArrowTip
from janim.items.geometry.line import Line
from janim.items.points import Group
from janim.items.text.text import Text
from janim.typing import JAnimColor, RangeSpecifier
from janim.utils.bezier import interpolate, outer_interpolate
from janim.utils.dict_ops import merge_dicts_recursively
from janim.utils.simple_functions import fdiv


class NumberLine(Line):
    '''
    数轴
    '''

    tip_config_d = dict(
        back_width=0.25,
        body_length=0.25
    )
    '''
    箭头的默认属性
    '''

    decimal_number_config_d = dict(
        num_decimal_places=0,
        font_size=16
    )
    '''
    数字的默认属性
    '''

    def __init__(
        self,
        x_range: RangeSpecifier = (-8, 8, 1),
        *,
        unit_size: int = 1,
        color: JAnimColor = GREY_B,
        stroke_radius: float = 0.01,
        width: float | None = None,
        include_tip: bool = False,                              # 是否显示箭头
        tip_config: dict = {},                                  # 箭头属性
        include_ticks: bool = True,                             # 是否显示刻度
        tick_size: float = 0.1,                                 # 刻度大小
        longer_tick_multiple: float = 1.5,                      # 长刻度大小倍数
        numbers_with_elongated_ticks: Iterable[float] = [],     # 指定哪些数字是长刻度
        include_numbers: bool = False,                          # 是否显示数字
        numbers_to_exclude: Iterable[float] = [],               # 需要排除的数字
        line_to_number_direction: np.ndarray = DOWN,            # 详见 get_number_item
        line_to_number_buff: float = MED_SMALL_BUFF,            # 详见 get_number_item
        decimal_number_config: dict = {},                       # 数字属性
        **kwargs
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

        self.numbers_with_elongated_ticks = list(numbers_with_elongated_ticks)
        self.numbers_to_exclude = list(numbers_to_exclude)
        if include_tip:
            self.numbers_to_exclude.append(self.x_max)

        self.line_to_number_direction = line_to_number_direction
        self.line_to_number_buff = line_to_number_buff

        self.decimal_number_config = merge_dicts_recursively(
            self.decimal_number_config_d,
            decimal_number_config
        )

        super().__init__(
            self.x_min * RIGHT, self.x_max * RIGHT,
            color=color,
            stroke_radius=stroke_radius,
            **kwargs
        )

        if width:
            self.points.set_width(width)
            self.unit_size = self.get_unit_size()
        else:
            self.points.scale(self.unit_size)
        self.points.to_center()

        index = 0

        if include_tip:
            self.add_tip(**self.tip_config)
            self.tip_index = index
            index += 1
        else:
            self.tip_index = None

        if include_ticks:
            self.add_ticks()
            self.ticks_index = index
            index += 1
        else:
            self.ticks_index = None

        if include_numbers:
            self.add_numbers()
            self.numbers_index = index
            index += 1
        else:
            self.numbers_index = None

    @property
    def tip(self) -> ArrowTip | None:
        return None if self.tip_index is None else self[self.tip_index]

    @property
    def ticks(self) -> Group[Line] | None:
        return None if self.ticks_index is None else self[self.ticks_index]

    @property
    def numbers(self) -> Group[Text] | None:
        return None if self.numbers_index is None else self[self.numbers_index]

    def get_unit_size(self) -> float:
        return self.points.length / (self.x_max - self.x_min)

    def get_tick_range(self) -> np.ndarray:
        tmp = self.x_min // self.x_step
        mod = self.x_min % self.x_step
        if mod >= 1e-5:
            tmp += 1
        x_min = self.x_step * tmp

        tmp = self.x_max // self.x_step
        mod = self.x_max % self.x_step
        if self.x_step - mod < 1e-5:
            tmp += 1.5
        else:
            tmp += 0.5
        x_max = self.x_step * tmp

        r = np.arange(x_min, x_max, self.x_step)
        return r

    def add_ticks(
        self,
        excluding: Iterable[float] | None = None,
    ) -> Group[Line]:
        if excluding is None:
            excluding = self.numbers_to_exclude

        ticks = Group()
        for x in self.get_tick_range():
            if np.isclose(excluding, x).any():
                continue

            size = self.tick_size
            if np.isclose(self.numbers_with_elongated_ticks, x).any():
                size *= self.longer_tick_multiple
            ticks.add(self.get_tick(x, size))
        self.add(ticks)
        return ticks

    def get_tick(self, x: float, size: float | None = None) -> Line:
        if size is None:
            size = self.tick_size
        result = Line(size * DOWN, size * UP)
        result.points.rotate(self.points.angle)
        result.points.move_to(self.number_to_point(x))
        result.stroke.set_rgbas([self.stroke.get()[0]])
        return result

    def add_numbers(
        self,
        x_values: Iterable[float] | None = None,
        excluding: Iterable[float] | None = None,
        font_size: int = 24,
        **kwargs
    ) -> Group[Text]:
        if x_values is None:
            x_values = self.get_tick_range()

        if excluding is None:
            excluding = self.numbers_to_exclude

        numbers = Group()
        for x in x_values:
            if np.isclose(excluding, x).any():
                continue
            numbers.add(self.get_number_item(x, font_size=font_size, **kwargs))
        self.add(numbers)
        return numbers

    def get_number_item(
        self,
        x: float,
        direction: np.ndarray | None = None,
        buff: float | None = None,
        **number_config
    ) -> Text:
        number_config = self.decimal_number_config.copy()
        number_config.update(number_config)

        if direction is None:
            direction = self.line_to_number_direction
        if buff is None:
            buff = self.line_to_number_buff

        places = number_config.pop('num_decimal_places')

        num_item = Text(str(round(x, places)), **number_config)
        num_item.points.next_to(
            self.number_to_point(x),
            direction=direction,
            buff=buff
        )
        if x < 0 and direction[0] == 0:
            # Align without the minus sign
            num_item.points.shift(num_item[0][0].points.box.width * LEFT / 2)
        return num_item

    def number_to_point(self, number: float | np.ndarray) -> np.ndarray:
        alpha = (number - self.x_min) / (self.x_max - self.x_min)
        return outer_interpolate(self.points.get_start(), self.points.get_end(), alpha)

    def point_to_number(self, point: np.ndarray) -> float:
        start = self.points.get_start()
        end = self.points.get_end()
        vect = end - start
        proportion = fdiv(
            np.dot(point - start, vect),
            np.dot(end - start, vect),
        )
        return interpolate(self.x_min, self.x_max, proportion)

    def n2p(self, number: float) -> np.ndarray:
        '''``number_to_point`` 的缩写'''
        return self.number_to_point(number)

    def p2n(self, point: np.ndarray) -> float:
        '''``point_to_number`` 的缩写'''
        return self.point_to_number(point)


class UnitInterval(NumberLine):
    def __init__(
        self,
        x_range: RangeSpecifier = (0, 1, 0.1),
        *,
        unit_size: int = 10,
        numbers_with_elongated_ticks: Iterable[float] = [0, 1],
        decimal_number_config: dict = dict(
            num_decimal_places=1
        ),
        **kwargs
    ) -> None:
        '''
        单位长度数轴（0~1，分10段）
        '''
        super().__init__(
            x_range,
            unit_size=unit_size,
            numbers_with_elongated_ticks=numbers_with_elongated_ticks,
            decimal_number_config=decimal_number_config,
            **kwargs
        )
