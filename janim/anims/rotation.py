
from janim.anims.updater import DataUpdater, UpdaterParams
from janim.components.points import Cmpt_Points
from janim.constants import C_LABEL_ANIM_STAY, ORIGIN, OUT
from janim.items.item import Item
from janim.items.points import Points
from janim.camera.camera import Camera
from janim.typing import Vect
from janim.utils.rate_functions import linear


class Rotate(DataUpdater):
    '''
    旋转，默认对角度进行平滑插值

    - 参数和旋转基本一致
    - ``absolute`` 参数是为了兼容摄像机物件，对于非摄像机物件该参数无效
    '''
    label_color = C_LABEL_ANIM_STAY

    def __init__(
        self,
        item: Item,
        angle: float,
        *,
        axis: Vect = OUT,
        about_point: Vect | None = None,
        about_edge: Vect = ORIGIN,
        root_only: bool = False,
        absolute: bool = True,
        **kwargs
    ):
        if about_point is None:
            box = item.astype(Points).points.self_box if root_only else item.astype(Points).points.box
            about_point = box.get(about_edge)

        if isinstance(item, Camera):
            def func(data: Camera, p: UpdaterParams) -> None:
                data.points.rotate(p.alpha * angle,
                                   axis=axis,
                                   absolute=absolute,
                                   about_point=about_point,
                                   root_only=True)
        else:
            def func(data: Item, p: UpdaterParams) -> None:
                points = data.components.get('points', None)
                if points is None or not isinstance(points, Cmpt_Points):
                    return  # pragma: no cover
                points.rotate(p.alpha * angle, axis=axis, about_point=about_point, root_only=True)

        super().__init__(item, func, root_only=root_only, **kwargs)


class Rotating(Rotate):
    '''
    旋转，默认对角度进行线性插值
    '''
    def __init__(self, item: Points, angle: float, *, rate_func=linear, **kwargs):
        super().__init__(item, angle, rate_func=rate_func, **kwargs)
