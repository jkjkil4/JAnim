from __future__ import annotations

import types
from typing import TYPE_CHECKING, Iterable, Protocol, Self, runtime_checkable

if TYPE_CHECKING:
    import numpy as np

    from janim.anims.animation import Animation

type Vect = Iterable[float] | np.ndarray
type VectArray = Iterable[Vect] | np.ndarray

type JAnimColor = str | Iterable[float] | np.ndarray
type ColorArray = Iterable[JAnimColor] | np.ndarray

type Alpha = float
type AlphaArray = Iterable[float] | np.ndarray

type Rgba = Iterable[float] | np.ndarray
type RgbaArray = Iterable[Rgba] | np.ndarray

type RangeSpecifier = tuple[float, float] | tuple[float, float, float]

type ForeverType = types.EllipsisType


@runtime_checkable
class SupportsApartAlpha(Protocol):
    def apart_alpha(self, n: int) -> None: ...


class SupportsAnim(Protocol):
    """
    可传入 :class:`~.AnimGroup` 的对象，需要具有 ``__anim__`` 方法

    因为可传入 :class:`~.AnimGroup` 的对象分为两种：

    - 本身就是 :class:`~.Animation` 对象

    - 具有 ``__anim__`` 方法，这个方法在调用后返回一个 :class:`~.Animation` 对象

    由于 :class:`~.Animation` 对象本身就实现了 ``__anim__`` 方法返回自己，
    所以用 :class:`SupportsAnim` 作为它们的统称，并会被 ``AnimGroup._get_animation_objects`` 统一转化
    """
    def __anim__(self) -> Animation: ...


@runtime_checkable
class SupportsTracking(Protocol):
    """
    定义了可直接被 :class:`~.Cmpt_Data` 所跟踪的对象类型

    对于没有实现这些方法的对象，使用 :meth:`~.Cmpt_Data.register_funcs` 另行定义类型的这三个方法
    """
    def copy(self) -> Self: ...

    def not_changed(self, other: Self) -> bool: ...

    def interpolate(self, other: Self, alpha: float) -> Self: ...


def t_(*x):
    """
    提供给 janim-toolbox VS Code 插件，用于标注其中包含的字符串需要 Typst 高亮
    """
    return x[0] if len(x) == 1 else x
