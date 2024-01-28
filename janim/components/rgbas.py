from __future__ import annotations

from typing import Self, Iterable

import numpy as np
from colour import Color

from janim.components.component import Component
from janim.utils.signal import Signal
from janim.utils.unique_nparray import UniqueNparray
from janim.utils.data import AlignedData
from janim.utils.bezier import interpolate
from janim.utils.iterables import resize_with_interpolation
from janim.typing import JAnimColor, ColorArray, Alpha, AlphaArray, RgbaArray


class Cmpt_Rgbas(Component):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._rgbas = UniqueNparray()
        self.clear()

    def copy(self) -> Self:
        cmpt_copy = super().copy()
        cmpt_copy._rgbas = UniqueNparray()
        cmpt_copy._rgbas.data = self._rgbas.data
        return cmpt_copy

    def __eq__(self, other: Cmpt_Rgbas) -> bool:
        return id(self.get()) == id(other.get())

    @staticmethod
    def align_for_interpolate(cmpt1: Cmpt_Rgbas, cmpt2: Cmpt_Rgbas):
        len1, len2 = len(cmpt1.get()), len(cmpt2.get())

        if len1 == len2:
            if cmpt1 == cmpt2:
                return AlignedData(cmpt1, cmpt1, cmpt1)
            # cmpt1 != cmpt2
            return AlignedData(cmpt1, cmpt2, Cmpt_Rgbas())

        if len1 > len2:
            return AlignedData(cmpt1, cmpt2.copy().resize(len1), Cmpt_Rgbas())

        # len1 < len2
        return AlignedData(cmpt1.copy().resize(len2), cmpt2, Cmpt_Rgbas())

    def interpolate(self, cmpt1: Cmpt_Rgbas, cmpt2: Cmpt_Rgbas, alpha: float) -> None:
        if cmpt1 == cmpt2:
            return

        self.set(interpolate(cmpt1.get(), cmpt2.get(), alpha))

    # region 颜色数据 | Colors

    def get(self) -> np.ndarray:
        return self._rgbas.data

    @staticmethod
    def format_rgbas(rgbas: RgbaArray) -> np.ndarray:
        if not isinstance(rgbas, np.ndarray):
            rgbas = np.array(rgbas)

        assert rgbas.ndim == 2
        assert rgbas.shape[1] == 4
        return rgbas

    @staticmethod
    def format_colors(colors: ColorArray) -> np.ndarray:
        if not isinstance(colors, np.ndarray):
            colors = np.array([
                color
                if isinstance(color, Iterable) and not isinstance(color, str)
                else Color(color).rgb

                for color in colors
            ])

        assert colors.ndim == 2
        assert colors.shape[1] == 3
        return colors

    @staticmethod
    def format_alphas(alphas: AlphaArray) -> np.ndarray:
        if not isinstance(alphas, np.ndarray):
            alphas = np.array(alphas)

        assert alphas.ndim == 1
        return alphas

    @Signal
    def set_rgbas(self, rgbas: np.ndarray) -> Self:
        self._rgbas.data = rgbas
        return self

    def set(
        self,
        color: JAnimColor | ColorArray = None,
        alpha: Alpha | AlphaArray = None,
        root_only: bool = False
    ) -> Self:
        '''
        - ``colors`` 表示传入的 ``RGB`` 颜色数据，可以是单个颜色也可以颜色数组
          （对于单个数据，支持 ``#FF0000`` ``'red'`` ``[1, 0, 0.5]`` 的表示）
        - ``alphas`` 表示传入的透明度数据，可以是单个数也可以是一个数组
          （对于单个数据，``1`` 表示不透明，``0`` 表示完全透明）
        - 默认情况下会将所有子物件也设置成指定的颜色，传入 ``root_only=True`` 可以只设置根物件的

        特殊传参：

        - 当 ``colors`` 为四分量 ``RGBA`` 颜色数据时，
        则同时表示了 ``colors`` 和 ``alphas`` 二者，因此不能再传入 ``alphas`` 参数
        '''
        if color is None and alpha is None:
            return

        def is_single_color(value: Iterable) -> bool:
            if isinstance(value, str):
                return True
            if isinstance(value[0], str):
                return False
            return not isinstance(value[0], Iterable)

        if color is not None and is_single_color(color):
            color = [color]
        if alpha is not None and not isinstance(alpha, Iterable):
            alpha = [alpha]

        if alpha is None and not isinstance(color[0], str) and len(color[0]) == 4:
            rgbas = self.format_rgbas(color)

            self.set_rgbas(rgbas)

            if not root_only and self.bind is not None:
                for item in self.bind.at_item.walk_descendants(self.bind.decl_cls):
                    cmpt = getattr(item, self.bind.key)
                    if isinstance(cmpt, Cmpt_Rgbas):
                        cmpt.set_rgbas(rgbas)
        else:
            if color is not None:
                color = self.format_colors(color)
            if alpha is not None:
                alpha = self.format_alphas(alpha)

            def set_to(cmpt: Cmpt_Rgbas):
                cmpt_color = cmpt.get()[:, :3] if color is None else color
                cmpt_alpha = cmpt.get()[:, 3] if alpha is None else alpha
                length = max(len(cmpt_color), len(cmpt_alpha))

                rgbas = np.hstack([
                    resize_with_interpolation(cmpt_color.astype(float), length),
                    resize_with_interpolation(cmpt_alpha.astype(float), length).reshape((length, 1))
                ])
                cmpt.set_rgbas(rgbas)

            set_to(self)

            if not root_only and self.bind is not None:
                for item in self.bind.at_item.walk_descendants(self.bind.decl_cls):
                    cmpt = getattr(item, self.bind.key)
                    if isinstance(cmpt, Cmpt_Rgbas):
                        set_to(cmpt)

        return self

    def clear(self) -> Self:
        self.set(np.full((1, 4), 1))
        return self

    def reverse(self) -> Self:
        self.set_rgbas(self.get()[::-1])
        return self

    def resize(self, length: int) -> Self:
        self.set(resize_with_interpolation(self.get(), length))
        return self

    def count(self) -> int:
        return len(self.get())

    # endregion
