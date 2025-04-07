import unittest

import numpy as np

from janim.utils.data import Array

class TestArray(unittest.TestCase):
    def test(self):
        arr = Array()

        arr1 = []
        arr2 = np.array([[1, 2], [5, 1]])

        arr.data = arr1
        self.assertIsNot(arr._data, arr1)

        arr3 = arr._data
        self.assertIs(arr3, arr._data)

        arr.data = arr2
        self.assertIsNot(arr._data, arr2)
        self.assertIsNot(arr3, arr._data)
