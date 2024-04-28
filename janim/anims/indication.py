from __future__ import annotations

from janim.anims.timeline import Timeline
from janim.anims.updater import DataUpdater, UpdaterParams
from janim.constants import GREY, ORIGIN, YELLOW
from janim.items.geometry.arc import Dot
from janim.items.item import Item
from janim.items.points import Points
from janim.typing import JAnimColor, Vect
from janim.utils.config import Config
from janim.utils.rate_functions import RateFunc, there_and_back
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
        dot = Dot(
            radius=Config.get.frame_x_radius + Config.get.frame_y_radius,
            fill_color=color,
            fill_alpha=0,
        )
        target_data: Item.Data[Dot] = Dot(radius=0, fill_color=color, fill_alpha=alpha).ref_data()
        self.timeline.track(dot)

        def updater(data: Item.Data[Dot], p: UpdaterParams):
            if isinstance(point_or_item, Item):
                target = self.timeline.get_stored_data_at_right(point_or_item, p.global_t)
                target_point = target.cmpt.points.box.get(about_edge)
            else:
                target_point = point_or_item

            target_data.cmpt.points.move_to(target_point)
            data.interpolate(data, target_data, p.alpha)

        super().__init__(dot, updater, duration=duration, **kwargs)


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

        def updater(data: Item.Data[Points], p: UpdaterParams) -> None:
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

    def create_extra_data(self, data: Item.Data[Points]) -> Item.Data[Points] | None:
        if not isinstance(data.item, Points):
            return None
        data_copy = data._copy(data)
        data_copy.cmpt.points.scale(self.scale_factor, about_point=self.about_point)
        for cmpt in data_copy.components.values():
            if not isinstance(cmpt, Cmpt_Rgbas):
                continue
            cmpt.set(self.color)
        return data_copy
