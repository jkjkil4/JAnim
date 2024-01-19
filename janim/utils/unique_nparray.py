from typing import Iterable

import numpy as np


class UniqueNparray:
    '''
    使得 `data` 在修改（赋值）后必定是不同的 id

    实际上也有意外情况，例如 ``self.data[...] = ...`` 之类的操作（尽量避免）
    '''
    def __init__(self):
        self._data = np.array([])

    @property
    def data(self) -> np.ndarray:
        return self._data

    @data.setter
    def data(self, data: np.ndarray | Iterable) -> None:
        if not isinstance(data, np.ndarray):
            self._data = np.array(data)
        else:
            self._data = data.copy()

    def __eq__(self, other) -> None:
        if not isinstance(other, UniqueNparray):
            return False
        return id(self._data) == id(other._data)

    def __hash__(self) -> int:
        return id(self._data)
