try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from typing import Iterable

import numpy as np

Vect = Iterable[float] | np.ndarray
VectArray = Iterable[Vect] | np.ndarray
