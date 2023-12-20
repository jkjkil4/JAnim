import unittest

import numpy as np

from janim.utils.unique_nparray import UniqueNparray

class UniqueNparrayTest(unittest.TestCase):
    def test(self):
        arr = UniqueNparray()
        
        arr1 = np.array([])
        arr2 = np.array([[1, 2], [5, 1]])

        arr.data = arr1
        self.assertIsNot(arr.data, arr1)

        arr3 = arr.data
        self.assertIs(arr3, arr.data)

        arr.data = arr2
        self.assertIsNot(arr.data, arr2)
        self.assertIsNot(arr3, arr.data)

if __name__ == '__main__':
    unittest.main()
