from typing import TYPE_CHECKING, Iterable, Protocol, runtime_checkable

from janim.utils.data import AlignedData

if TYPE_CHECKING:
    import numpy as np

type Vect = Iterable[float] | np.ndarray
type VectArray = Iterable[Vect] | np.ndarray


@runtime_checkable
class SupportsInterpolate[T](Protocol):
    @staticmethod
    def align_for_interpolate(obj1: object, obj2: object) -> AlignedData[T]: ...

    def interpolate(self, obj1: object, obj2: object): ...
