try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

import colour

from typing import Tuple, Union, Iterable

JAnimColor = Union[str, colour.Color, Iterable]
RangeSpecifier = Tuple[float, float, float] | Tuple[float, float]
