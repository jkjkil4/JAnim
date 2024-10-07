import unittest

import numpy as np

from janim.items.item import Item
from janim.components.component import CmptInfo
from janim.components.rgbas import Cmpt_Rgbas


class RgbasTest(unittest.TestCase):
    def assertNparrayEqual(self, np1, np2):
        self.assertListEqual(np.array(np1).tolist(), np.array(np2).tolist())

    def assertNparrayClose(self, np1, np2):
        np1 = np.array(np1)
        np2 = np.array(np2)
        self.assertListEqual(np.isclose(np1, np2).tolist(), np.full(np1.shape, True).tolist())

    def test_rgbas(self) -> None:
        class MyItem(Item):
            color = CmptInfo(Cmpt_Rgbas)

        item = MyItem()
        item.color.set(['red', 'white', 'blue'])

        self.assertNparrayEqual(
            item.color.get(),
            [[1, 0, 0, 1], [1, 1, 1, 1], [0, 0, 1, 1]]
        )

        item.color.set(alpha=[1, 0])

        self.assertNparrayEqual(
            item.color.get(),
            [[1, 0, 0, 1], [1, 1, 1, 0.5], [0, 0, 1, 0]]
        )

        item.color.set(alpha=0.7)

        self.assertNparrayClose(
            item.color.get(),
            [[1, 0, 0, 0.7], [1, 1, 1, 0.7], [0, 0, 1, 0.7]]
        )

        item.color.set(color='red')

        self.assertNparrayClose(
            item.color.get(),
            [[1, 0, 0, 0.7], [1, 0, 0, 0.7], [1, 0, 0, 0.7]]
        )

        item.color.set([1, 1, 1, 1])
        item.color.set()

        self.assertEqual(item.color.count(), 1)
        self.assertNparrayEqual(
            item.color.get(),
            [[1, 1, 1, 1]]
        )
