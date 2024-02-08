from __future__ import annotations

from typing import Iterable, Self

import numpy as np

from janim.components.component import Component
from janim.utils.bezier import interpolate
from janim.utils.data import AlignedData
from janim.utils.iterables import resize_with_interpolation
from janim.utils.unique_nparray import UniqueNparray

DEFAULT_RADIUS = 0.05


class Cmpt_Radius(Component):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._radii = UniqueNparray()
        self.clear()

    def copy(self) -> Self:
        cmpt_copy = super().copy()
        cmpt_copy._radii = self._radii.copy()
        return cmpt_copy

    def __eq__(self, other: Cmpt_Radius) -> bool:
        return self._radii.is_share(other._radii)

    @classmethod
    def align_for_interpolate(cls, cmpt1: Cmpt_Radius, cmpt2: Cmpt_Radius):
        len1, len2 = len(cmpt1.get()), len(cmpt2.get())

        cmpt1_copy = cmpt1.copy()
        cmpt2_copy = cmpt2.copy()

        if len1 < len2:
            cmpt1_copy.resize(len2)
        elif len1 > len2:
            cmpt1_copy.resize(len1)

        return AlignedData(cmpt1_copy, cmpt2_copy, cmpt1_copy.copy())

    def interpolate(self, cmpt1: Cmpt_Radius, cmpt2: Cmpt_Radius, alpha: float, *, path_func=None) -> None:
        if cmpt1 == cmpt2:
            return

        self.set(interpolate(cmpt1.get(), cmpt2.get(), alpha))

    # region 半径数据 | Radii

    def get(self) -> np.ndarray:
        return self._radii.data

    def set(
        self,
        radius: float | Iterable[float],
        *,
        root_only: bool = False,
    ) -> Self:
        if not isinstance(radius, Iterable):
            radius = [radius]
        radii = np.array(radius)

        self._radii.data = radii
        if not root_only and self.bind is not None:
            for item in self.bind.at_item.walk_descendants(self.bind.decl_cls):
                cmpt = getattr(item, self.bind.key)
                if isinstance(cmpt, Cmpt_Radius):
                    cmpt._radii.data = radii

        return self

    def clear(self) -> Self:
        self.set(np.full(1, DEFAULT_RADIUS))

    def reverse(self) -> Self:
        self.set(self.get()[::-1])
        return self

    def resize(self, length: int) -> Self:
        self.set(resize_with_interpolation(self.get(), max(1, length)))
        return self

    def count(self) -> int:
        return len(self.get())

    # endregion
