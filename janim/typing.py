import types
from typing import TYPE_CHECKING, Iterable, Protocol, runtime_checkable

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
    '''
    有些直接是 :class:`~.Animation`，而有些不是，但可以转化为 :class:`~.Animation，
    因此用 :class:`SupportsAnim` 作为它们的统称，并会被 `AnimGroup._get_animation_objects` 统一转化
    '''
    def __anim__(self) -> 'Animation': ...


def t_(*x):
    '''
    提供给 janim-toolbox vscode 插件，用于标注其中包含的字符串需要 Typst 高亮
    '''
    return x[0] if len(x) == 1 else x
