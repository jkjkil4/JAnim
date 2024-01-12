from __future__ import annotations

from typing import Self

import numpy as np

from janim.components.component import Component
from janim.utils.signal import Signal
from janim.utils.unique_nparray import UniqueNparray
from janim.typing import VectArray


class Cmpt_Points(Component):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._points = UniqueNparray()
        self.set([])

    def get(self) -> np.ndarray:
        return self._points.data

    @Component.as_able
    def get_all(_) -> np.ndarray:
        info = Component.extract_as(_)

        return np.vstack([
            getattr(item, info.cmpt_name).get()
            for item in info.origin.walk_self_and_descendants(info.as_type)
        ])

    @Signal
    def set(self, points: VectArray) -> Self:
        '''
        设置点坐标数据，每个坐标点都有三个分量

        使用形如 ``set_points([[1.5, 3, 2], [2, 1.5, 0]])`` 的形式

        Set point coordinate data, with each point having three components.

        Use a format like ``set_points([[1.5, 3, 2], [2, 1.5, 0]])``.
        '''
        if not isinstance(points, np.ndarray):
            points = np.array(points)
        if points.size == 0:
            points = np.zeros((0, 3))

        assert points.ndim == 2
        assert points.shape[1] == 3

        cnt_changed = len(points) != len(self._points.data)

        self._points.data = points

        if cnt_changed:
            Cmpt_Points.set.emit(self, key='count')
        Cmpt_Points.set.emit(self)

        return self
