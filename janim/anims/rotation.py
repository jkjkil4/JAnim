
from janim.anims.updater import TimeBasedUpdater, UpdaterParams
from janim.items.item import Item
from janim.items.points import Points
from janim.components.points import Cmpt_Points
from janim.typing import Vect
from janim.utils.rate_functions import linear
from janim.constants import ORIGIN


class Rotate(TimeBasedUpdater):
    label_color = (64, 181, 126)

    def __init__(
        self,
        item: Item,
        angle: float,
        *,
        about_point: Vect | None = None,
        about_edge: Vect = ORIGIN,
        root_only: bool = False,
        **kwargs
    ):
        if about_point is None:
            box = item.astype(Points).points.self_box if root_only else item.astype(Points).points.box
            about_point = box.get(about_edge)

        def func(data: Item.Data, p: UpdaterParams) -> None:
            points = data.components.get('points', None)
            if points is None or not isinstance(points, Cmpt_Points):
                return
            points.rotate(p.alpha * angle, about_point=about_point, root_only=True)

        super().__init__(item, func, root_only=root_only, **kwargs)


class Rotating(Rotate):
    def __init__(self, item: Points, angle: float, rate_func=linear, **kwargs):
        super().__init__(item, angle, rate_func=rate_func, **kwargs)
