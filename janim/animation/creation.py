from abc import abstractmethod, ABCMeta
from janim.items.item import Item

from janim.items.vitem import VItem
from janim.animation.animation import ItemAnimation

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
