from typing import Callable
from abc import abstractmethod, ABCMeta

from janim.constants import *
from janim.items.item import Item
from janim.items.vitem import VItem
from janim.animation.animation import ItemAnimation
from janim.animation.composition import Succession
from janim.animation.transform import ReplacementTransform

class ShowPartial(ItemAnimation, metaclass=ABCMeta):
    '''
    Abstract class for ShowCreation and ShowPassingFlash
    '''
    def create_interpolate_datas(self) -> tuple:
        return [self.item_for_anim.copy().get_family()]
    
    def is_null_item(self, item: Item, interpolate_data: tuple) -> bool:
        start_item, = interpolate_data
        return not start_item.has_points()

    def interpolate_subitem(
        self,
        item: VItem,
        interpolate_data: tuple,
        alpha: float
    ) -> None:
        start_item, = interpolate_data
        item.pointwise_become_partial(
            start_item, *self.get_bounds(alpha)
        )

    @abstractmethod
    def get_bounds(self, alpha: float) -> tuple[float, float]:
        pass

class ShowCreation(ShowPartial):
    def __init__(self, item: Item, lag_ratio: float = 1.0, **kwargs) -> None:
        super().__init__(item, lag_ratio=lag_ratio, **kwargs)

    def get_bounds(self, alpha: float) -> tuple[float, float]:
        return (0, alpha)
    
class Uncreate(ShowCreation):
    def interpolate(self, alpha) -> None:
        super().interpolate(1 - alpha)

class DrawBorderThenFill(Succession):
    def __init__(
        self,
        vitem: VItem,
        run_time: float = 2.0,
        stroke_width: float = 0.02,
        stroke_color: JAnimColor = None,
        draw_border_anim_config: dict = {},
        fill_anim_config: dict = {},
        **kwargs
    ) -> None:
        outline = vitem.copy()
        outline.set_fill(opacity=0)
        for item in outline.get_family():
            if stroke_color or np.all(vitem.get_stroke_width() == 0.0):
                item.set_stroke(stroke_color or item.get_fill_rgbas())
            item.set_stroke_width(stroke_width)

        if 'lag_ratio' not in draw_border_anim_config:
            draw_border_anim_config['lag_ratio'] = 0.0

        super().__init__(
            ShowCreation(outline, **draw_border_anim_config),
            ReplacementTransform(outline, vitem, **fill_anim_config),
            run_time=run_time,
            **kwargs
        )
