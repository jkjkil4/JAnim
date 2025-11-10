
import numbers
from typing import Iterable

import numpy as np

from janim.constants import (DOWN, GREY_B, LEFT, MED_SMALL_BUFF, ORIGIN, RIGHT,
                             UP, UR)
from janim.items.geometry.arrow import ArrowTip
from janim.items.geometry.line import Line
from janim.items.points import Group, MarkedItem, Points
from janim.items.svg.typst import TypstMath
from janim.items.text import Text
from janim.typing import JAnimColor, RangeSpecifier, Vect
from janim.utils.bezier import interpolate, outer_interpolate
from janim.utils.dict_ops import merge_dicts_recursively
from janim.utils.simple_functions import fdiv


class NumberLine(MarkedItem, Line):
    '''
    数轴

    参数：

    -   ``x_range``:

        使用 ``[最小值, 最大值, 步长]`` 设定数轴的表示范围以及刻度步长

        或使用 ``[最小值, 最大值]``，步长默认为 1

    -   ``unit_size``: 数轴单位长度

    -   ``length``: 数轴总长，当该值设置时，会忽略 ``unit_size``

    -   ``center``: 创建后是否使整体居中

    箭头参数：

    -   ``include_tip``: 是否显示箭头，默认为 ``False`` 即不显示

    -   ``tip_config``: 提供给箭头的额外参数，另见 :meth:`~.VItem.add_tip`

    刻度参数：

    -   ``include_ticks``: 是否显示刻度，默认为 ``True`` 即显示

    -   ``tick_size``: 刻度大小

    -   ``longer_tick_multiple``: 长刻度在 ``tick_size`` 基础上的倍数

    -   ``numbers_with_elongated_ticks``: 提供一个列表，指定哪些数字是长刻度

    数字参数：

    -   ``include_numbers``: 是否显示数字

    -   ``numbers_to_exclude``: 需要排除的数字

    -   ``line_to_number_direction``: 数字放在刻度点的哪个方向

    -   ``line_to_number_buff``: 数字与刻度点的间距
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
        unit_size: int = 1,                                     # 数轴单位长度
        width: float | None = None,
        length: float | None = None,                            # 数轴总长
        center: bool = True,                                    # 创建后是否使整体居中
        color: JAnimColor = GREY_B,
        stroke_radius: float = 0.01,
        # tip
        include_tip: bool = False,                              # 是否显示箭头
        tip_config: dict = {},                                  # 箭头属性
        # ticks
        include_ticks: bool = True,                             # 是否显示刻度
        tick_size: float = 0.1,                                 # 刻度大小
        longer_tick_multiple: float = 1.5,                      # 长刻度大小倍数
        numbers_with_elongated_ticks: Iterable[float] = [],     # 指定哪些数字是长刻度
        # numbers
        include_numbers: bool = False,                          # 是否显示数字
        numbers_to_exclude: Iterable[float] = [],               # 需要排除的数字
        line_to_number_direction: np.ndarray = DOWN,            # 数字放在刻度点的哪个方向
        line_to_number_buff: float = MED_SMALL_BUFF,            # 数字与刻度点的间距
        decimal_number_config: dict = {},                       # 数字属性
        **kwargs
    ) -> None:
        if width is not None:
            from janim.utils.deprecation import deprecated
            deprecated(
                'width',
                'length',
                remove=(4, 3)
            )
            length = width

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
        self.mark.set_points([ORIGIN])

        if length:
            self.points.set_width(length, about_point=ORIGIN)
            self.unit_size = self.get_unit_size()
        else:
            self.points.scale(self.unit_size, about_point=ORIGIN)

        if center:
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
        return self.compute_tick_range(self.x_min, self.x_max, self.x_step)

    @staticmethod
    def compute_tick_range(x_min: float, x_max: float, x_step: float) -> np.ndarray:
        # 这里的处理本质上是通过 x_min // x_step * x_step 得出 “比 x_min 低的第一个刻度位置”
        # 但是这样得到的刻度位置会跑到数轴外面，所以，如果 x_min 没有刚好落在刻度位置，就需要把它加 1 往数轴里面调整
        # “没有刚好落在刻度位置” 这个判定需要考虑浮点误差，所以这里使用了 mod >= 1e-5 而不是 mod != 0
        tmp = x_min // x_step
        mod = x_min % x_step
        if mod >= 1e-5:
            tmp += 1
        r_x_min = x_step * tmp

        # 这里的处理本质上是通过 x_max // x_step * x_step 得出 “比 x_max 低的第一个刻度位置”
        # 但是因为 arange 不会取到最后一项，所以需要手动加上 0.5 使得 arange 能取到这个刻度位置
        # 不过这里 x_step - mod < 1e-5 时却是加上 1.5，因为判定成立时 x_max 已经几乎在下一个刻度位置了，理应算成这个位置，所以多加了 1
        tmp = x_max // x_step
        mod = x_max % x_step
        if x_step - mod < 1e-5:
            tmp += 1.5
        else:
            tmp += 0.5
        r_x_max = x_step * tmp

        r = np.arange(r_x_min, r_x_max, x_step)
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
        if np.isclose(x, 0.):
            x = 0.

        number_config = self.decimal_number_config.copy()
        number_config.update(number_config)

        if direction is None:
            direction = self.line_to_number_direction
        if buff is None:
            buff = self.line_to_number_buff

        places = number_config.pop('num_decimal_places')
        num = round(x, places)

        num_item = Text(str(num), **number_config)
        num_item.points.next_to(
            self.number_to_point(x),
            direction=direction,
            buff=buff
        )
        if x < 0 and direction[0] == 0:
            # Align without the minus sign
            num_item.points.shift(num_item[0][0].points.box.width * LEFT / 2)
        return num_item

    def get_axis_label(
        self,
        label: str | Points,
        *,
        alpha: float = 1,
        direction: Vect = UR,
        buff=MED_SMALL_BUFF,
        ensure_on_screen: bool = False,
        **kwargs
    ) -> TypstMath | Points:
        '''
        得到坐标轴标签文字

        如果 ``label`` 是字符串，则会将其作为 Typst 公式解析成为 :class:`~.TypstMath` 物件

        物件会被放置到合适的地方，默认情况下是坐标轴尖端的旁边，具体来说由 ``alpha`` ``direction`` 和 ``buff`` 控制：

        - ``alpha`` 控制物件被放到坐标轴哪个点的旁边，该数值表示坐标轴上的百分比位置，例如默认的 ``1`` 即为坐标轴末尾，``0`` 则为坐标轴起点

        - ``direction`` 控制物件被放到前面所述的点的哪个方向，默认是 ``UR`` 表示右上方

        - ``buff`` 控制物件与前面所述的点的间距

        如果坐标轴比较长，坐标轴标签有可能会超出屏幕，
        此时如果设置 ``ensure_on_screen=True``，坐标轴标签会自动调整位置移动到默认屏幕区域内
        '''
        if isinstance(label, str):
            label = TypstMath(label, **kwargs)
            label.points.scale(1.4)
        label.points.next_to(self.points.pfp(alpha), direction, buff=buff)
        if ensure_on_screen:
            label.points.shift_onto_screen_along_direction(self.points.vector, buff=MED_SMALL_BUFF)
        return label

    def number_to_point(self, number: float | Iterable[float] | np.ndarray) -> np.ndarray:
        '''
        传入数值得到在坐标轴上对应的位置

        传入的可以是：

        - 单个数，得到单个坐标，表示这个数在坐标轴上的位置；
          例如 ``n2p(2)`` 得到 2 在坐标轴上的位置

        - 多个数，得到一组坐标，分别表示这些数在坐标轴上的位置；
          例如 ``n2p([0, 2, 4])`` 分别得到 0、2、4 在坐标轴上的位置
        '''
        if not isinstance(number, numbers.Real):
            number = np.asarray(number)
        alpha = (number - self.x_min) / (self.x_max - self.x_min)
        return outer_interpolate(self.points.get_start(), self.points.get_end(), alpha)

    def point_to_number(self, point: np.ndarray) -> float:
        '''
        传入坐标将其映射到坐标轴上，返回在坐标轴上的数值
        '''
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
    '''
    单位长度数轴（只有 0~1 的区段，其中细分 10 段）
    '''

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
        super().__init__(
            x_range,
            unit_size=unit_size,
            numbers_with_elongated_ticks=numbers_with_elongated_ticks,
            decimal_number_config=decimal_number_config,
            **kwargs
        )
