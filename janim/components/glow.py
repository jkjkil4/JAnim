from __future__ import annotations

from typing import Iterable, Self

import numpy as np
from colour import Color

from janim.anims.method_updater_meta import register_updater
from janim.components.component import Component
from janim.typing import Alpha, JAnimColor, Rgba
from janim.utils.bezier import interpolate
from janim.utils.data import AlignedData, Array

DEFAULT_GLOW_ARRAY = Array()
DEFAULT_GLOW_ARRAY.data = [1, 1, 0, 0]


class Cmpt_Glow[ItemT](Component[ItemT]):
    '''
    泛光组件
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rgba = DEFAULT_GLOW_ARRAY.copy()
        self._size: float = 0.2

    def copy(self) -> Self:
        cmpt_copy = super().copy()
        cmpt_copy._rgba = self._rgba.copy()
        # _size 已通过 super().copy() 拷贝
        return cmpt_copy

    def become(self, other: Cmpt_Glow) -> Self:
        if not self._rgba.is_share(other._rgba):
            self._rgba = other._rgba.copy()
        self._size = other._size
        return self

    def not_changed(self, other: Cmpt_Glow) -> bool:
        return self._rgba.is_share(other._rgba) and self._size == other._size

    @classmethod
    def align_for_interpolate(cls, cmpt1: Cmpt_Glow, cmpt2: Cmpt_Glow):
        cmpt1_copy = cmpt1.copy()
        cmpt2_copy = cmpt2.copy()
        return AlignedData(cmpt1_copy, cmpt2_copy, cmpt1_copy.copy())

    def interpolate(self, cmpt1: Cmpt_Glow, cmpt2: Cmpt_Glow, alpha: float, *, path_func=None) -> None:
        if not cmpt1._rgba.is_share(cmpt2._rgba) or not cmpt1._rgba.is_share(self._rgba):
            if cmpt1._rgba.is_share(cmpt2._rgba):
                self._rgba = cmpt1._rgba.copy()
            else:
                self.set_rgba(interpolate(cmpt1.get(), cmpt2.get(), alpha))

        if cmpt1._size != cmpt2._size or cmpt1._size != self._size:
            self._size = interpolate(cmpt1._size, cmpt2._size, alpha)

    def set_rgba(self, rgba: Rgba) -> Self:
        self._rgba.data = rgba
        return self

    @staticmethod
    def format_rgba(rgba: Rgba) -> np.ndarray:
        if not isinstance(rgba, np.ndarray):
            rgba = np.array(rgba)

        assert rgba.ndim == 1
        assert rgba.shape[0] == 4
        return rgba

    @staticmethod
    def format_color(color: JAnimColor) -> np.ndarray:
        rgb = np.array(
            color
            if isinstance(color, Iterable) and not isinstance(color, str)
            else Color(color).rgb
        )

        assert rgb.ndim == 1
        assert rgb.shape[0] == 3
        return rgb

    def _set_updater(self, p, color=None, alpha=None, size=None, *, root_only=False):
        if color is not None:
            self.mix(color, p.alpha, root_only=root_only)
        if alpha is not None:
            self.mix_alpha(alpha, p.alpha, root_only=root_only)
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
        '''
        - ``color`` 表示传入的 ``RGB`` 颜色数据，单个颜色
          （支持 ``'#FF0000'`` ``'red'`` ``[1, 0, 0.5]`` 的表示）
        - ``alpha`` 表示传入的透明度数据
          （``1`` 表示不透明，``0`` 表示完全透明）
        - ``size`` 表示泛光的大小
        - 默认情况下会将所有子物件也设置成指定的属性，传入 ``root_only=True`` 可以只设置根物件的

        特殊传参：

        - 当 ``color`` 为四分量 ``RGBA`` 颜色数据时，
          则同时表示了 ``color`` 和 ``alpha`` 二者，因此不能再传入 ``alpha`` 参数
        '''
        if color is not None or alpha is not None:
            if alpha is None and not isinstance(color, str) and len(color) == 4:
                rgba = self.format_rgba(color)

                self.set_rgba(rgba)

                for cmpt in self.walk_same_cmpt_of_self_and_descendants_without_mock(root_only):
                    cmpt.set_rgba(rgba)

            else:
                if color is not None:
                    color = self.format_color(color)

                for cmpt in self.walk_same_cmpt_of_self_and_descendants_without_mock(root_only):
                    cmpt_color = cmpt.get()[:3] if color is None else color
                    cmpt_alpha = cmpt.get()[3] if alpha is None else alpha
                    cmpt.set_rgba(np.array([*cmpt_color, cmpt_alpha]))

        if size is not None:
            for cmpt in self.walk_same_cmpt_of_self_and_descendants_without_mock(root_only):
                cmpt._size = size

        return self

    def get(self) -> np.ndarray:
        return self._rgba.data

    def get_size(self) -> None:
        return self._size

    @register_updater(
        lambda self, p, color, factor=0.5, *, root_only=False:
            self.mix(color, factor * p.alpha, root_only=root_only)
    )
    def mix(self, color: JAnimColor, factor: float = 0.5, *, root_only: bool = False) -> Self:
        color = self.format_color(color)
        for cmpt in self.walk_same_cmpt_of_self_and_descendants_without_mock(root_only):
            data = cmpt.get().copy()
            data[:3] *= 1 - factor
            data[:3] += color * factor
            cmpt.set(data)
        return self

    @register_updater(
        lambda self, p, alpha, factor=0.5, *, root_only=False:
            self.mix_alpha(alpha, factor * p.alpha, root_only=root_only)
    )
    def mix_alpha(self, alpha: Alpha, factor: float = 0.5, *, root_only: bool = False) -> Self:
        for cmpt in self.walk_same_cmpt_of_self_and_descendants_without_mock(root_only):
            data = cmpt.get().copy()
            data[3] *= 1 - factor
            data[3] += alpha * factor
            cmpt.set(data)
        return self
