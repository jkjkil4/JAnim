from __future__ import annotations

from typing import Self

import numpy as np

from janim.anims.method_updater_meta import register_updater
from janim.components.component import Component
from janim.components.points import DEFAULT_POINTS_ARRAY, PointsFn
from janim.typing import Vect, VectArray
from janim.utils.bezier import interpolate
from janim.utils.data import AlignedData
from janim.utils.iterables import resize_and_repeatedly_extend
from janim.utils.paths import PathFunc, straight_path
from janim.utils.signal import Signal


class Cmpt_Mark[ItemT](Component[ItemT]):
    names: list[str] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._points = DEFAULT_POINTS_ARRAY.copy()

    def copy(self) -> Self:
        cmpt_copy = super().copy()
        cmpt_copy._points = self._points.copy()
        return cmpt_copy

    def become(self, other: Cmpt_Mark) -> Self:
        if not self._points.is_share(other._points.copy()):
            self._points = other._points.copy()
        return self

    def not_changed(self, other: Cmpt_Mark) -> bool:
        return self._points.is_share(other._points)

    @classmethod
    def align_for_interpolate(cls, cmpt1: Cmpt_Mark, cmpt2: Cmpt_Mark) -> AlignedData[Self]:
        len1, len2 = len(cmpt1.get_points()), len(cmpt2.get_points())

        cmpt1_copy = cmpt1.copy()
        cmpt2_copy = cmpt2.copy()

        if len1 < len2:
            cmpt1_copy.set_points(resize_and_repeatedly_extend(cmpt1.get_points(), len(cmpt2.get_points())))
        elif len1 > len2:
            cmpt2_copy.set_points(resize_and_repeatedly_extend(cmpt2.get_points(), len(cmpt1.get_points())))

        return AlignedData(cmpt1_copy, cmpt2_copy, cmpt1_copy.copy())

    def interpolate(
        self,
        cmpt1: Self,
        cmpt2: Self,
        alpha: float,
        *,
        path_func: PathFunc = straight_path
    ) -> None:
        if not cmpt1._points.is_share(cmpt2._points) or not cmpt1._points.is_share(self._points):
            if cmpt1._points.is_share(cmpt2._points):
                self._points = cmpt1._points.copy()
            else:
                self.set_points(path_func(cmpt1.get_points(), cmpt2.get_points(), alpha))

    def get_points(self) -> np.ndarray:
        '''
        直接得到记录的所有坐标点数据
        '''
        return self._points.data

    def get(self, index: int | str = 0) -> np.ndarray:
        '''
        得到指定索引（默认为 0）记录的坐标点
        '''
        index = self.format_index(index)
        return self._points.data[index]

    def set_points(self, points: VectArray) -> Self:
        '''
        直接设置记录的所有坐标点数据，不会对 ``points`` 产生影响
        '''
        points = np.asarray(points)
        if points.size == 0:
            points = np.zeros((0, 3))

        assert points.ndim == 2
        assert points.shape[1] == 3

        self._points.data = points
        return self

    @register_updater(
        lambda self, p, point, index=0, *, root_only=False:
            self.set(interpolate(np.asarray(point), self.get(index), p.alpha), index, root_only=root_only)
    )
    @Signal
    def set(self, point: Vect, index: int | str = 0, *, root_only: bool = False) -> Self:
        '''
        设置指定索引（默认为 0）记录的坐标点

        更改会同步到 ``points`` 上
        '''
        point = np.asarray(point)

        assert point.ndim == 1
        assert point.shape[0] == 3

        index = self.format_index(index)
        vector = point - self.get(index)
        self.set_points(self.get_points() + vector)
        Cmpt_Mark.set.emit(self, vector, root_only)
        return self

    def format_index(self, index: int | str) -> int:
        return self.names.index(index) if isinstance(index, str) else index

    def apply_points_fn(self, func: PointsFn, about_point: Vect | None = None) -> Self:
        '''
        将所有点作为单独的一个参数传入 ``func``，并将 ``func`` 返回的结果作为新的点坐标数据

        用于同步与 ``points`` 的变换，已经在 :class:`~.MarkedItem` 里绑定了同步，不需要手动设置和调用
        '''
        if about_point is None:
            self.set_points(func(self.get_points()))
        else:
            self.set_points(func(self.get_points() - about_point) + about_point)
        return self
