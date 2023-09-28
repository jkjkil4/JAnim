try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from typing import Tuple

RangeSpecifier = Tuple[float, float, float] | Tuple[float, float]
