from typing import Optional, Callable
from abc import abstractmethod, ABCMeta

from janim.constants import *
from janim.items.item import Item
from janim.items.vitem import VItem
from janim.animation.animation import ItemAnimation
from janim.utils.rate_functions import RateFunc, double_smooth, linear
from janim.utils.bezier import integer_interpolate

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
    '''
    显示物件的创建过程
    '''
    def __init__(self, item: Item, lag_ratio: float = 1.0, **kwargs) -> None:
        super().__init__(item, lag_ratio=lag_ratio, **kwargs)

    def get_bounds(self, alpha: float) -> tuple[float, float]:
        return (0, alpha)
    
class Uncreate(ShowCreation):
    '''
    显示物件的销毁过程（`ShowCreation` 的倒放）
    '''
    def interpolate(self, alpha) -> None:
        super().interpolate(1 - alpha)

class DrawBorderThenFill(ItemAnimation):
    '''
    画出边缘，然后填充内部
    '''
    def __init__(
        self,
        vitem: VItem,
        run_time: float = 2.0,
        stroke_width: float = 0.02,
        stroke_color: JAnimColor = None,
        rate_func: RateFunc = double_smooth,
        draw_border_anim_config: dict = {},
        fill_anim_config: dict = {},
        **kwargs
    ) -> None:
        super().__init__(vitem, run_time=run_time, rate_func=rate_func, **kwargs)
        self.stroke_width = stroke_width
        self.stroke_color = stroke_color
        self.draw_border_anim_config = draw_border_anim_config
        self.fill_anim_config = fill_anim_config
    
    def create_interpolate_datas(self) -> tuple:
        vitem: VItem = self.item_for_anim

        start = vitem.copy()

        vitem.set_fill(opacity=0).set_stroke_width(self.stroke_width)
        outline = vitem.copy()
        for item in outline.get_family():
            item.outline_fully_displayed = False
            if self.stroke_color or np.all(vitem.get_stroke_width() == 0.0):
                item.set_stroke(self.stroke_color or item.get_fill_rgbas())
        
        return (
            start.get_family(),
            outline.get_family(),
            ItemAnimation.compute_npdata_to_copy_and_interpolate(start, outline)
        )
    
    def interpolate_subitem(self, item: VItem, interpolate_data: tuple, alpha: float) -> None:
        start, outline, npdata_to_copy_and_interpolate = interpolate_data
        index, subalpha = integer_interpolate(0, 2, alpha)
        
        if index == 0:
            item.pointwise_become_partial(outline, 0, subalpha)
        else:
            if not outline.outline_fully_displayed:
                item.pointwise_become_partial(outline, 0, 1)
                outline.outline_fully_displayed = True
            item.interpolate(outline, start, subalpha, None, npdata_to_copy_and_interpolate)

class Write(DrawBorderThenFill):
    '''
    显示书写过程（对每个子物件应用 DrawBorderThenFill）
    '''
    def __init__(
        self,
        vitem: VItem,
        run_time: Optional[float] = None,
        lag_ratio: Optional[float] = None,
        rate_func: RateFunc = linear,
        **kwargs
    ) -> None:
        length = len(vitem.family_members_with_points())
        if run_time is None:
            run_time = 1 if length < 15 else 2
        if lag_ratio is None:
            lag_ratio = min(4.0 / (length + 1.0), 0.2)
        super().__init__(vitem, run_time=run_time, lag_ratio=lag_ratio, rate_func=rate_func, **kwargs)

