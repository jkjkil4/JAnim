from __future__ import annotations

from typing import Iterable, Self

import numpy as np
from colour import Color

from janim.components.component import Component
from janim.typing import Alpha, AlphaArray, ColorArray, JAnimColor, RgbaArray
from janim.utils.bezier import interpolate
from janim.utils.data import AlignedData, Array
from janim.utils.iterables import resize_with_interpolation

DEFAULT_RGBAS_ARRAY = Array()
DEFAULT_RGBAS_ARRAY.data = np.full((1, 4), 1)


class Cmpt_Rgbas[ItemT](Component[ItemT]):
    '''
    颜色组件
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._rgbas = DEFAULT_RGBAS_ARRAY.copy()

    def copy(self) -> Self:
        cmpt_copy = super().copy()
        cmpt_copy._rgbas = self._rgbas.copy()
        return cmpt_copy

    def become(self, other: Cmpt_Rgbas) -> Self:
        if not self._rgbas.is_share(other._rgbas):
            self._rgbas = other._rgbas.copy()
        return self

    def not_changed(self, other: Cmpt_Rgbas) -> bool:
        return self._rgbas.is_share(other._rgbas)

    @classmethod
    def align_for_interpolate(cls, cmpt1: Cmpt_Rgbas, cmpt2: Cmpt_Rgbas):
        len1, len2 = len(cmpt1.get()), len(cmpt2.get())

        cmpt1_copy = cmpt1.copy()
        cmpt2_copy = cmpt2.copy()

        if len1 < len2:
            cmpt1_copy.resize(len2)
        elif len1 > len2:
            cmpt1_copy.resize(len1)

        return AlignedData(cmpt1_copy, cmpt2_copy, cmpt1_copy.copy())

    def interpolate(self, cmpt1: Cmpt_Rgbas, cmpt2: Cmpt_Rgbas, alpha: float, *, path_func=None) -> None:
        if not cmpt1._rgbas.is_share(cmpt2._rgbas):
            self.set_rgbas(interpolate(cmpt1.get(), cmpt2.get(), alpha))

    def is_transparent(self) -> None:
        return (self._rgbas.data[:, 3] == 0).all()

    # region 颜色数据 | Colors

    def get(self) -> np.ndarray:
        return self._rgbas.data

    @staticmethod
    def format_rgbas(rgbas: RgbaArray) -> np.ndarray:
        '''
        将传入值转换为数值数组
        '''
        if not isinstance(rgbas, np.ndarray):
            rgbas = np.array(rgbas)

        assert rgbas.ndim == 2
        assert rgbas.shape[1] == 4
        return rgbas

    @staticmethod
    def format_colors(colors: ColorArray) -> np.ndarray:
        '''
        将 ``ColorArray`` （每个元素有可能是 字符串、``[r, g, b]`` ）
        格式化为元素仅有 ``[r, g, b]`` 的数值数组的格式
        '''
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
        '''
        将传入值转为数值数组
        '''
        if not isinstance(alphas, np.ndarray):
            alphas = np.array(alphas)

        assert alphas.ndim == 1
        return alphas

    def set_rgbas(self, rgbas: RgbaArray) -> Self:
        '''
        直接设置 rgba 数据
        '''
        self._rgbas.data = rgbas
        return self

    def set(
        self,
        color: JAnimColor | ColorArray | None = None,
        alpha: Alpha | AlphaArray | None = None,
        *,
        root_only: bool = False,
    ) -> Self:
        '''
        - ``colors`` 表示传入的 ``RGB`` 颜色数据，可以是单个颜色也可以颜色数组
          （对于单个数据，支持 ``'#FF0000'`` ``'red'`` ``[1, 0, 0.5]`` 的表示）
        - ``alphas`` 表示传入的透明度数据，可以是单个数也可以是一个数组
          （对于单个数据，``1`` 表示不透明，``0`` 表示完全透明）
        - 默认情况下会将所有子物件也设置成指定的颜色，传入 ``root_only=True`` 可以只设置根物件的

        特殊传参：

        - 当 ``colors`` 为四分量 ``RGBA`` 颜色数据时，
          则同时表示了 ``colors`` 和 ``alphas`` 二者，因此不能再传入 ``alphas`` 参数
        '''
        if color is None and alpha is None:
            return self

        def is_single_color(value: Iterable) -> bool:
            if isinstance(value, str):
                return True
            if isinstance(value[0], str):
                return False
            return not isinstance(value[0], Iterable)

        if color is not None and is_single_color(color):
            color = [color]
        if alpha is not None and isinstance(alpha, (int, float)):
            alpha = [alpha]

        if alpha is None and not isinstance(color[0], str) and len(color[0]) == 4:
            rgbas = self.format_rgbas(color)

            self.set_rgbas(rgbas)

            for cmpt in self.walk_same_cmpt_of_self_and_descendants_without_mock(root_only):
                cmpt.set_rgbas(rgbas)

        else:
            if color is not None:
                color = self.format_colors(color)
            if alpha is not None:
                alpha = self.format_alphas(alpha)

            for cmpt in self.walk_same_cmpt_of_self_and_descendants_without_mock(root_only):
                cmpt_color = cmpt.get()[:, :3] if color is None else color
                cmpt_alpha = cmpt.get()[:, 3] if alpha is None else alpha
                length = max(len(cmpt_color), len(cmpt_alpha))

                rgbas = np.hstack([
                    resize_with_interpolation(cmpt_color.astype(float), length),
                    resize_with_interpolation(cmpt_alpha.astype(float), length).reshape((length, 1))
                ])
                cmpt.set_rgbas(rgbas)

        return self

    def clear(self) -> Self:
        '''
        将颜色数据重置为默认值
        '''
        self.set(DEFAULT_RGBAS_ARRAY.data)
        return self

    def reverse(self) -> Self:
        self.set_rgbas(self.get()[::-1])
        return self

    def resize(self, length: int) -> Self:
        self.set(resize_with_interpolation(self.get(), max(1, length)))
        return self

    def count(self) -> int:
        return len(self.get())

    def apart_alpha(self, n: int) -> Self:
        '''
        对每一个颜色数据应用 :func:`~.apart_alpha`
        '''
        rgbas = self.get().copy()
        for i in range(len(rgbas)):
            rgbas[i, 3] = apart_alpha(rgbas[i, 3], n)
        self.set_rgbas(rgbas)
        return self

    def fade(self, factor: float | Iterable[float], *, root_only: bool = False) -> Self:
        for cmpt in self.walk_same_cmpt_of_self_and_descendants_without_mock(root_only):
            rgbas = cmpt.get().copy()
            rgbas[:, 3] *= 1 - factor
            cmpt.set_rgbas(rgbas)

        return self

    # endregion


def merge_alpha(alpha: float, n: int) -> float:
    '''
    计算透明度 ``alpha`` 在重叠 ``n`` 次混合后的透明度
    '''
    result = alpha
    for _ in range(n - 1):
        result = 1 - (1 - result) * (1 - alpha)

    return result


def apart_alpha(alpha: float, n: int, *, eps: float = 1e-3) -> float:
    '''
    将透明度分离为 ``n`` 份，使得这 ``n`` 份混合后仍然表现为原来的透明度

    使得在对齐时产生的重复部分能够更好地渲染
    '''
    if alpha >= 1:
        return 1
    if alpha <= 0:
        return 0

    tpl1 = (0, 0)
    tpl2 = (1, 1)

    # REFACTOR: 有无更好的方式？
    while tpl2[0] - tpl1[0] > eps:
        mid_single = (tpl1[0] + tpl2[0]) / 2
        mid_merged = merge_alpha(mid_single, n)
        if mid_merged == alpha:
            return mid_single

        if mid_merged < alpha:
            tpl1 = (mid_single, mid_merged)
        else:
            tpl2 = (mid_single, mid_merged)

    return mid_single
