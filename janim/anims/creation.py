
from typing import Callable

import numpy as np

from janim.anims.updater import TimeBasedUpdater, UpdaterParams
from janim.components.vpoints import Cmpt_VPoints
from janim.constants import NAN_POINT
from janim.items.item import Item


class ShowPartial(TimeBasedUpdater):
    def __init__(
        self,
        item: Item,
        bound_func: Callable[[UpdaterParams], tuple[int, int]],
        *,
        auto_close_path: bool = False,
        become_at_end: bool = False,
        root_only: bool = False,
        **kwargs
    ):
        def func(data: Item.Data, p: UpdaterParams) -> None:
            cmpt = data.components.get('points', None)
            if cmpt is None or not isinstance(cmpt, Cmpt_VPoints):
                return
            if not cmpt.has():
                return

            if not auto_close_path:
                cmpt.pointwise_become_partial(cmpt, *bound_func(p))
            else:
                end_indices = np.array(cmpt.get_subpath_end_indices())
                begin_indices = np.array([0, *[indice + 2 for indice in end_indices[:-1]]])

                points = cmpt.get()
                cond1 = np.isclose(points[begin_indices], points[end_indices]).all(axis=1)

                cmpt.pointwise_become_partial(cmpt, *bound_func(p))

                points = cmpt.get()
                cond2 = ~np.isclose(points[begin_indices], points[end_indices]).all(axis=1)
                where = np.where(cond1 & cond2)[0]

                if len(where) == 0:
                    return

                end_indices = end_indices[where]
                begin_indices = begin_indices[where]

                points[end_indices] = points[begin_indices]
                points[end_indices - 1] = (points[begin_indices] + points[end_indices - 2]) / 2
                if end_indices[-1] == len(points) - 1:
                    end_indices = end_indices[:-1]
                points[end_indices + 1] = NAN_POINT

                cmpt.set(points)

        super().__init__(item, func, become_at_end=become_at_end, root_only=root_only, **kwargs)


class Create(ShowPartial):
    '''
    显示物件的创建过程
    '''
    def __init__(self, item: Item, auto_close_path: bool = True, **kwargs):
        super().__init__(item, lambda p: (0, p.alpha), auto_close_path=auto_close_path, **kwargs)
