from __future__ import annotations

import numbers
from functools import cache
from typing import Iterable, Self

import numpy as np

from janim.anims.method_updater_meta import register_updater
from janim.components.core.attrs import ComponentAttrs
from janim.components.core.component import Component
from janim.utils.bezier import interpolate
from janim.utils.data import AlignedData, owned, readonly_array
from janim.utils.iterables import resize_with_interpolation


@cache
def _get_array(radius: float) -> np.ndarray:
    return owned(readonly_array(np.full(1, radius, dtype=np.float32)))


class Cmpt_Radius[ItemT](Component[ItemT]):
    """
    半径组件，被用于 :class:`DotCloud` 的点半径，以及 :class:`VItem` 的轮廓线粗细
    """

    _attrs = ComponentAttrs()
    _radii = _attrs.ndarray(np.zeros(1, dtype=np.float32))
    default_radius = _attrs.float()

    def __cmpt_init__(self, default_radius: float, *args, **kwargs):
        self.default_radius = default_radius
        self._radii = _get_array(default_radius)

    @classmethod
    def align_for_interpolate(  # type: ignore
        cls, cmpt1: Cmpt_Radius, cmpt2: Cmpt_Radius
    ) -> AlignedData[Cmpt_Radius]:
        len1, len2 = len(cmpt1.get()), len(cmpt2.get())

        cmpt1_copy = cmpt1.copy()
        cmpt2_copy = cmpt2.copy()

        if len1 < len2:
            cmpt1_copy.resize(len2)
        elif len1 > len2:
            cmpt1_copy.resize(len1)

        return AlignedData(cmpt1_copy, cmpt2_copy, cmpt1_copy.copy())

    def interpolate(
        self, cmpt1: Cmpt_Radius, cmpt2: Cmpt_Radius, alpha: float, *, path_func=None
    ) -> None:
        if id(cmpt1._radii) != id(cmpt2._radii) or id(cmpt1._radii) != id(self._radii):
            if id(cmpt1._radii) == id(cmpt2._radii):
                self._radii = owned(cmpt1._radii.copy())
            else:
                self.set(interpolate(cmpt1.get(), cmpt2.get(), alpha), root_only=True)

    # region 半径数据 | Radii

    def get(self) -> np.ndarray:
        """
        得到半径数据
        """
        return self._radii

    def _set_updater(self, p, radius, *, root_only=False):
        if isinstance(radius, numbers.Real):
            radius = [radius]
        data2 = np.asarray(radius)

        for cmpt in self.walk_same_cmpt_of_self_and_descendants(root_only):
            data1 = cmpt.get()
            len1, len2 = len(data1), len(data2)
            if len1 < len2:
                data1_resized = resize_with_interpolation(data1, len2)
                cmpt.set(interpolate(data1_resized, data2, p.alpha), root_only=True)
            elif len1 > len2:
                data2_resized = resize_with_interpolation(data2, len1)
                cmpt.set(interpolate(data1, data2_resized, p.alpha), root_only=True)

    @register_updater(_set_updater)
    def set(
        self,
        radius: float | Iterable[float],
        *,
        root_only: bool = False,
    ) -> Self:
        """
        设置半径数据
        """
        if isinstance(radius, numbers.Real):
            radius = [radius]  # type: ignore
        radius = owned(np.asarray(radius, dtype=np.float32))

        self._radii = radius

        if not root_only:
            for cmpt in self.walk_same_cmpt_of_descendants():
                cmpt._radii = radius

        return self

    def clear(self) -> Self:
        """
        将半径数据重置为默认值
        """
        self.set(np.full(1, self.default_radius))
        return self

    def reverse(self) -> Self:
        self.set(self.get()[::-1])
        return self

    def resize(self, length: int) -> Self:
        self.set(resize_with_interpolation(self.get(), max(1, length)), root_only=True)
        return self

    def count(self) -> int:
        return len(self.get())

    def scale(self, factor: float, *, root_only: bool = False) -> Self:
        """
        缩放半径数据
        """
        self._radii = owned(self._radii * factor)

        if not root_only:
            for cmpt in self.walk_same_cmpt_of_descendants():
                cmpt._radii = owned(cmpt._radii * factor)

        return self

    # endregion
