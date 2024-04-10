from __future__ import annotations

from typing import Iterable

import numpy as np


class UniqueNparray:
    '''
    使得 `data` 在修改（赋值）后必定是不同的 id

    实际上也有意外情况，例如 ``self.data[...] = ...`` 之类的操作（尽量避免）
    '''
    def __init__(self, dtype=np.float64):
        self._data = np.array([], dtype=dtype)
        self._dtype = dtype

    def len(self) -> int:
        return len(self._data)

    @property
    def data(self) -> np.ndarray:
        # TODO: Optimize by setting WRITEABLE=False
        return self._data.copy()

    @data.setter
    def data(self, data: np.ndarray | Iterable) -> None:
        if not isinstance(data, np.ndarray):
            self._data = np.array(data, dtype=self._dtype)
        else:
            self._data = data.copy().astype(self._dtype)

    def copy(self) -> UniqueNparray:
        ret = UniqueNparray()
        ret._data = self._data
        return ret

    def is_share(self, other: UniqueNparray) -> bool:
        return id(self._data) == id(other._data)
