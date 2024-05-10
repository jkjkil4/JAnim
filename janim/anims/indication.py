from __future__ import annotations

import numpy as np

from janim.anims.animation import Animation
from janim.anims.composition import AnimGroup, Succession
from janim.anims.creation import Create, ShowPartial
from janim.anims.fading import FadeOut
from janim.anims.updater import DataUpdater, UpdaterParams
from janim.components.rgbas import Cmpt_Rgbas
from janim.constants import GREY, ORIGIN, RIGHT, TAU, YELLOW
from janim.items.geometry.arc import Circle, Dot
from janim.items.geometry.line import Line
from janim.items.item import Item
from janim.items.points import Group, Points
from janim.items.shape_matchers import SurroundingRect
from janim.items.vitem import VItem
from janim.typing import JAnimColor, Vect
from janim.utils.bezier import interpolate
from janim.utils.config import Config
from janim.utils.rate_functions import RateFunc, rush_from, there_and_back


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


class ShowPassingFlash(ShowPartial):
    def __init__(
        self,
        item: Points,
        *,
        time_width: float = 0.1,
        auto_close_path: bool = False,
        **kwargs
    ):
        def bound_func(p: UpdaterParams) -> tuple[float, float]:
            upper = interpolate(0, 1 + time_width, p.alpha)
            lower = upper - time_width
            upper = min(upper, 1)
            lower = max(lower, 0)
            return (lower, upper)

        super().__init__(
            item,
            bound_func,
            auto_close_path=auto_close_path,
            hide_at_begin=False,
            show_at_end=False,
            become_at_end=False,
            **kwargs
        )


class ShowCreationThenDestruction(ShowPassingFlash):
    '''展现创建动画后展现销毁动画'''
    def __init__(
        self,
        item: Points,
        *,
        time_width: float = 2.0,
        duration: float = 1,
        **kwargs
    ):
        super().__init__(item, time_width=time_width, duration=duration, **kwargs)


class ShowCreationThenFadeOut(Succession):
    '''展现创建动画后展现淡出动画'''
    def __init__(self, item: Points, create_kwargs: dict = {}, fadeout_kwargs: dict = {}, **kwargs):
        super().__init__(
            Create(item, **create_kwargs),
            FadeOut(item, **fadeout_kwargs),
            **kwargs
        )


class AnimationOnSurroundingRect(AnimGroup):
    def __init__(
        self,
        item: Points,
        rect_anim: type[Animation],
        surrounding_rect_config: dict = {},
        **kwargs
    ):
        self.item = item
        self.surrounding_rect_config = surrounding_rect_config

        rect = self.create_rect()
        anim = rect_anim(rect, **kwargs)
        self.apply_updater(anim)

        super().__init__(anim)

    def create_rect(self) -> SurroundingRect:
        rect = SurroundingRect(
            self.item,
            **self.surrounding_rect_config
        )
        rect.points.move_to(rect.points.box.center - self.item.points.box.center)
        return rect

    def updater(self, data: Points, p: UpdaterParams):
        data.points.shift(self.item.current().points.box.center)

    def apply_updater(self, anim: Animation):
        if isinstance(anim, DataUpdater):
            anim.add_post_updater(self.updater)
        elif isinstance(anim, AnimGroup):
            for sub in anim.anims:
                self.apply_updater(sub)


class ShowPassingFlashAround(AnimationOnSurroundingRect):
    '''不完整线条在指定物件周围环绕一圈的动画'''
    def __init__(self, item: Points, **kwargs) -> None:
        super().__init__(item, ShowPassingFlash, **kwargs)


class ShowCreationThenDestructionAround(AnimationOnSurroundingRect):
    '''在指定物件周围先创建出完整线条再销毁线条的动画'''
    def __init__(self, item: Points, **kwargs) -> None:
        super().__init__(item, ShowCreationThenDestruction, **kwargs)


class ShowCreationThenFadeAround(AnimationOnSurroundingRect):
    '''在指定物件周围先创建出完整线条再淡出线条的动画'''
    def __init__(self, item: Points, **kwargs) -> None:
        super().__init__(item,
                         ShowCreationThenFadeOut,
                         create_kwargs=dict(auto_close_path=False),
                         **kwargs)


class Flash(ShowCreationThenDestruction):
    def __init__(
        self,
        point_or_item: Vect | Points,
        *,
        color: JAnimColor = YELLOW,
        line_length: float = 0.2,
        num_lines: int = 12,
        flash_radius: float = 0.3,
        line_stroke_radius: float = 0.015,
        rate_func: RateFunc = rush_from,
        **kwargs
    ):
        self.point_or_item = point_or_item
        self.color = color
        self.line_length = line_length
        self.num_lines = num_lines
        self.flash_radius = flash_radius
        self.line_stroke_radius = line_stroke_radius

        self.lines = self.create_lines()
        super().__init__(self.lines, rate_func=rate_func, **kwargs)

        def updater(data: Points, p: UpdaterParams):
            if not isinstance(point_or_item, Points):
                pos = point_or_item
            else:
                pos = point_or_item.current().points.box.center
            data.points.shift(pos)

        self.add_post_updater(updater)

    def create_lines(self) -> Group:
        lines = Group()
        for angle in np.arange(0, TAU, TAU / self.num_lines):
            line = Line(ORIGIN, self.line_length * RIGHT)
            line.points.shift((self.flash_radius - self.line_length) * RIGHT)
            line.points.rotate(angle, about_point=ORIGIN)
            lines.add(line)
        lines(VItem) \
            .stroke.set(self.color) \
            .r.radius.set(self.line_stroke_radius)
        return lines
