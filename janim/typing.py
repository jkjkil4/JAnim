from typing import Iterable

import numpy as np

Vect = Iterable[float] | np.ndarray
VectArray = Iterable[Vect] | np.ndarray
