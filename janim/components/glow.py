from __future__ import annotations

from typing import Iterable, Self

import numpy as np
from colour import Color

from janim.anims.method_updater_meta import register_updater
from janim.components.component import Component
from janim.components.rgba import Cmpt_Rgba
from janim.typing import Alpha, JAnimColor, Rgba
from janim.utils.bezier import interpolate
from janim.utils.data import AlignedData, Array


class Cmpt_Glow[ItemT](Cmpt_Rgba[ItemT]):
    """
    泛光组件
    """

    DEFAULT_RGBA_ARRAY = Array.create([1, 1, 0, 0])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._size: float = 0.2

    def copy(self) -> Self:
        cmpt_copy = super().copy()
        # _size 已通过 super().copy() 拷贝
        return cmpt_copy

    def become(self, other: Cmpt_Glow) -> Self:
        super().become(other)
        self._size = other._size
        return self

    def not_changed(self, other: Cmpt_Glow) -> bool:
        return super().not_changed(other) and self._size == other._size

    def interpolate(
        self, cmpt1: Cmpt_Glow, cmpt2: Cmpt_Glow, alpha: float, *, path_func=None
    ) -> None:
        super().interpolate(cmpt1, cmpt2, alpha, path_func=path_func)

        if cmpt1._size != cmpt2._size or cmpt1._size != self._size:
            self._size = interpolate(cmpt1._size, cmpt2._size, alpha)

    def _set_updater(self, p, color=None, alpha=None, size=None, *, root_only=False):
        super()._set_updater(p, color, alpha, root_only=root_only)
        if size is not None:
            for cmpt in self.walk_same_cmpt_of_self_and_descendants_without_mock(root_only):
                cmpt._size = interpolate(cmpt._size, size, p.alpha)

    @register_updater(_set_updater)
    def set(
        self,
        color: JAnimColor | None = None,
        alpha: Alpha | None = None,
        size: float | None = None,
        *,
        root_only: bool = False,
    ) -> Self:
        """
        - ``color`` 表示传入的 ``RGB`` 颜色数据，单个颜色
          （支持 ``'#FF0000'`` ``'red'`` ``[1, 0, 0.5]`` 的表示）
        - ``alpha`` 表示传入的透明度数据
          （``1`` 表示不透明，``0`` 表示完全透明）
        - ``size`` 表示泛光的大小
        - 默认情况下会将所有后代物件也设置成指定的属性，传入 ``root_only=True`` 可以只设置根物件的

        特殊传参：

        - 当 ``color`` 为四分量 ``RGBA`` 颜色数据时，
          则同时表示了 ``color`` 和 ``alpha`` 二者，因此不能再传入 ``alpha`` 参数
        """
        super().set(color, alpha, root_only=root_only)

        if size is not None:
            for cmpt in self.walk_same_cmpt_of_self_and_descendants_without_mock(root_only):
                cmpt._size = size

        return self

    def get_size(self) -> float:
        return self._size
