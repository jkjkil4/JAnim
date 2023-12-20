try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from typing import Iterable

import numpy as np

Vect = Iterable[float]
VectArray = Iterable[Vect]
