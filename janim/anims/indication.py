from __future__ import annotations

import numpy as np

from janim.anims.updater import DataUpdater, UpdaterParams
from janim.constants import GREY, ORIGIN, YELLOW, TAU, RIGHT
from janim.items.geometry.arc import Dot
from janim.items.item import Item
from janim.items.points import Points, Group
from janim.items.geometry.line import Line
from janim.items.geometry.arc import Circle
from janim.items.vitem import VItem
from janim.typing import JAnimColor, Vect
from janim.utils.config import Config
from janim.utils.rate_functions import RateFunc, there_and_back
from janim.utils.bezier import interpolate
from janim.components.rgbas import Cmpt_Rgbas


class FocusOn(DataUpdater[Dot]):
    '''展现一个逐渐聚焦到指定物件的圆形缩小动画'''
    def __init__(
        self,
        point_or_item: Vect | Points,
        *,
        about_edge: Vect = ORIGIN,
        color: JAnimColor = GREY,
        alpha: float = 0.2,
        duration: float = 2,
        **kwargs
    ) -> None:
        dot1 = Dot(
            radius=Config.get.frame_x_radius + Config.get.frame_y_radius,
            fill_color=color,
            fill_alpha=0,
        )
        dot2 = Dot(radius=0, fill_color=color, fill_alpha=alpha)

        def updater(data: Dot, p: UpdaterParams):
            if isinstance(point_or_item, Item):
                target = point_or_item.current()
                target_point = target.points.box.get(about_edge)
            else:
                target_point = point_or_item

            dot2.points.move_to(target_point)
            data.interpolate(data, dot2, p.alpha)

        super().__init__(dot1, updater, duration=duration, **kwargs)
        self.timeline.track(dot1)


class Indicate(DataUpdater):
    '''展现指定物件以放大为黄色后回到原状的动画'''
    def __init__(
        self,
        item: Points,
        *,
        scale_factor: float = 1.2,
        color: JAnimColor = YELLOW,
        rate_func: RateFunc = there_and_back,
        root_only: bool = False,
        **kwargs
    ) -> None:
        box = item.points.self_box if root_only else item.points.box
        self.about_point = box.center
        self.scale_factor = scale_factor
        self.color = color

        def updater(data: Points, p: UpdaterParams) -> None:
            if p.extra_data is None:
                return
            data.interpolate(data, p.extra_data, p.alpha)

        super().__init__(
            item,
            updater,
            rate_func=rate_func,
            become_at_end=False,
            root_only=root_only,
            **kwargs
        )

    def create_extra_data(self, data: Item) -> Points | None:
        if not isinstance(data, Points):
            return None
        data_copy = data.store()
        data_copy.points.scale(self.scale_factor, about_point=self.about_point)
        for cmpt in data_copy.components.values():
            if not isinstance(cmpt, Cmpt_Rgbas):
                continue
            cmpt.set(self.color)
        return data_copy


# class Flash(DataUpdater):
#     def __init__(
#         self,
#         point_or_item: Vect | Item,
#         *,
#         color: JAnimColor = YELLOW,
#         line_length: float = 0.2,
#         num_lines: int = 12,
#         flash_radius: float = 0.3,
#         line_stroke_radius: float = 0.015,
#         **kwargs
#     ):
#         super().__init__(**kwargs)
#         self.point_or_item = point_or_item
#         self.color = color
#         self.line_length = line_length
#         self.num_lines = num_lines
#         self.flash_radius = flash_radius
#         self.line_stroke_radius = line_stroke_radius

#         self.lines = self.create_lines()
#         super().__init__()

#     def create_lines(self) -> Group:
#         lines = Group()
#         for angle in np.arange(0, TAU, TAU / self.num_lines):
#             line = Line(ORIGIN, self.line_length * RIGHT)
#             line.points.shift((self.flash_radius - self.line_length) * RIGHT)
#             line.points.rotate(angle, about_point=ORIGIN)
#             lines.add(line)
#         lines(VItem) \
#             .stroke.set(self.color) \
#             .r.radius.set(self.line_stroke_radius)
#         return lines


class CircleIndicate(DataUpdater[Circle]):
    def __init__(
        self,
        item: Points,
        *,
        color: JAnimColor = YELLOW,
        rate_func: RateFunc = there_and_back,
        scale: float = 1,
        **kwargs
    ):
        start = Circle(color=color, alpha=0)
        target = Circle(color=color)

        def updater(c: Circle, p: UpdaterParams):
            c.interpolate(start, target, p.alpha)
            c.points.surround(item.current())
            if scale != 1:
                c.points.scale(interpolate(scale, 1, p.alpha))

        super().__init__(
            start,
            updater,
            rate_func=rate_func,
            hide_at_begin=False,
            show_at_end=False,
            become_at_end=False,
            **kwargs
        )
