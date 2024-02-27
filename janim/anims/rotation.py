
from janim.anims.updater import TimeBasedUpdater
from janim.items.points import Points
from janim.utils.rate_functions import linear


class Rotate(TimeBasedUpdater[Points]):
    label_color = (64, 181, 126)

    def __init__(self, item: Points, angle: float, **kwargs):
        super().__init__(
            item,
            lambda data, p: data.cmpt.points.rotate(p.alpha * angle),
            **kwargs
        )


class Rotating(Rotate):
    def __init__(self, item: Points, angle: float, rate_func=linear, **kwargs):
        super().__init__(item, angle, rate_func=rate_func, **kwargs)
