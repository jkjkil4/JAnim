try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from typing import Iterable

Vect = Iterable[float]
VectArray = Iterable[Vect]
