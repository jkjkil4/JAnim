from typing import TYPE_CHECKING, Iterable, Protocol, runtime_checkable

from janim.utils.data import AlignedData

if TYPE_CHECKING:
    import numpy as np

type Vect = Iterable[float] | np.ndarray
type VectArray = Iterable[Vect] | np.ndarray

type JAnimColor = str | Iterable[float] | np.ndarray
type ColorArray = Iterable[JAnimColor] | np.ndarray

type Alpha = float
type AlphaArray = Iterable[float] | np.ndarray

type Rgba = Iterable[float] | np.ndarray
type RgbaArray = Iterable[Rgba] | np.ndarray

type RangeSpecifier = tuple[float, float] | tuple[float, float, float]


@runtime_checkable
class SupportsInterpolate[T](Protocol):
    @classmethod
    def align_for_interpolate(cls, obj1: object, obj2: object) -> AlignedData[T]: ...

    def interpolate(self, obj1: object, obj2: object, alpha: float, *, path_func): ...


@runtime_checkable
class SupportsApartAlpha(Protocol):
    def apart_alpha(self, n: int) -> None: ...
