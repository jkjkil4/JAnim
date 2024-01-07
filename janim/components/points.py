from __future__ import annotations

import numpy as np

from janim.components.component import Component, for_many
from janim.utils.signal import Signal
from janim.utils.unique_nparray import UniqueNparray
from janim.typing import Self, VectArray


class Cmpt_Points(Component):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._points = UniqueNparray()
        self.set_points([])

    def points(self) -> np.ndarray:
        return self._points.data

    @for_many
    def all_points(*many: Cmpt_Points) -> np.ndarray:
        print(many)

        # return np.vstack([one.points() for one in many])

    @Signal
    def set_points(self, points: VectArray) -> Self:
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
            Cmpt_Points.set_points.emit(self, key='count')
        Cmpt_Points.set_points.emit(self)

        return self
