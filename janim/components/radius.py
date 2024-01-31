from __future__ import annotations

from typing import Self, Iterable

import numpy as np

from janim.components.component import Component
from janim.utils.data import AlignedData
from janim.utils.unique_nparray import UniqueNparray
from janim.utils.bezier import interpolate
from janim.utils.iterables import resize_with_interpolation

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
        return id(self.get()) == id(other.get())

    @classmethod
    def align_for_interpolate(cls, cmpt1: Cmpt_Radius, cmpt2: Cmpt_Radius):
        len1, len2 = len(cmpt1.get()), len(cmpt2.get())

        if len1 == len2:
            if cmpt1 == cmpt2:
                return AlignedData(cmpt1, cmpt1, cmpt1)
            # cmpt1 != cmpt2
            return AlignedData(cmpt1, cmpt2, cls())

        if len1 > len2:
            return AlignedData(cmpt1, cmpt2.copy().resize(len1), cls())

        # len1 < len2
        return AlignedData(cmpt1.copy().resize(len2), cmpt2, cls())

    def interpolate(self, cmpt1: Cmpt_Radius, cmpt2: Cmpt_Radius, alpha: float) -> None:
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
        self.set(resize_with_interpolation(self.get(), length))
        return self

    def count(self) -> int:
        return len(self.get())

    # endregion
