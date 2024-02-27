
from janim.anims.updater import TimeBasedUpdater
from janim.items.points import Points
from janim.typing import Vect
from janim.utils.rate_functions import linear
from janim.constants import ORIGIN


class Rotate(TimeBasedUpdater[Points]):
    label_color = (64, 181, 126)

    def __init__(
        self,
        item: Points,
        angle: float,
        *,
        about_point: Vect | None = None,
        about_edge: Vect = ORIGIN,
        root_only=False,
        **kwargs
    ):
        if about_point is None:
            box = item.points.self_box if root_only else item.points.box
            about_point = box.get(about_edge)

        super().__init__(
            item,
            lambda data, p: data.cmpt.points.rotate(p.alpha * angle, about_point=about_point, root_only=True),
            root_only=root_only,
            **kwargs
        )


class Rotating(Rotate):
    def __init__(self, item: Points, angle: float, rate_func=linear, **kwargs):
        super().__init__(item, angle, rate_func=rate_func, **kwargs)
