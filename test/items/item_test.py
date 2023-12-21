from janim.typing import Self

import unittest

from janim.items.item import Item, Group

class ItemSetVal(Item):
    def __init__(self):
        super().__init__()
        self.val = 0

    def set_value(self, val) -> Self:
        self.val = val
        return self
    
    def get_value(self):
        return self.val

class ItemTest(unittest.TestCase):
    def test_simple_relation(self) -> None:
        m1, m2 = Item(), Item()
        m1.add(m2)
        self.assertIn(m1, m2.parents)
        self.assertIn(m2, m1.subitems)

        m1.remove(m2)
        self.assertNotIn(m1, m2.parents)
        self.assertNotIn(m2, m1.subitems)
    
    def test_get_family(self) -> None:
        m1, m2, m3, m4 = (Item() for _ in range(4))
        m1.add(m2, m3)
        m2.add(m4)
        self.assertEqual(m1.get_family(), [m1, m2, m4, m3])
    
    def test_refresh_required(self) -> None:
        class MyItem(Item):
            def __init__(self) -> None:
                super().__init__()
                self.cnt = 0    # 用于记录 `get_data` 真正被调用的次数
                                # Used to record the actual number of calls to `get_data`
                self.data = 0

            @Item.register_refresh_required
            def get_data(self) -> None:
                self.cnt += 1
                return self.data
        
        item = MyItem()
        
        # 一开始没调用 `get_data`，因此显然调用次数为 0
        # Initially, `get_data` has not been called, so the call count is obviously 0
        self.assertEqual(item.cnt, 0)

        # 在这十次中，只有第一次是有真正执行 `get_data` 的，因此执行后调用次数为 1
        # In these ten calls, only the first one actually executes `get_data`, so the call count becomes 1
        for i in range(10):
            item.get_data()
        self.assertEqual(item.cnt, 1)

        # 这里设置了 `data` 为 10，但是由于没有 `mark_refresh_required`，
        # 因此 `get_data` 的数据并没有被更新，所以应当为 0
        #
        # Here, `data` is set to 10, but without `mark_refresh_required`,
        # data of `get_data` is not updated, so it should be 0
        item.data = 10
        self.assertEqual(item.get_data(), 0)

        # 这里标记 `mark_refresh_required`，所以 `get_data` 可以得到更新，并且调用次数变为 2
        # Mark `mark_refresh_required` here, so `get_data` can be updated, and the call count becomes 2
        item.mark_refresh_required(MyItem.get_data)
        self.assertEqual(item.get_data(), 10)
        self.assertEqual(item.cnt, 2)

        # 之后这十次调用都没有真正调用 `get_data`，所以最终调用次数仍然为 2
        # In the next ten calls, `get_data` is not actually called, so the final call count remains 2
        for i in range(10):
            item.get_data()
        self.assertEqual(item.cnt, 2)

    def test_group_method(self) -> None:        
        class ItemA(Item): ...

        root = Group(
            g1 := Group(
                m1 := ItemSetVal(),
                m2 := ItemA()
            ),
            m3 := ItemSetVal(),
            m4 := ItemSetVal()
        )
        
        root.for_all.set_value(10)
        m4.set_value(20)

        self.assertEqual(root.for_all.get_value(), [10, 10, 20])

        self.assertEqual(root.get_family(), [root, g1, m1, m2, m3, m4])
        self.assertEqual(m1.get_value(), 10)
        self.assertEqual(m3.get_value(), 10)

    def test_group_method_advanced(self) -> None:
        class ItemA(Item): ...

        root = ItemSetVal().add(
            g1 := Group(
                m1 := ItemSetVal(),
                m2 := ItemA()
            ),
            m3 := ItemSetVal(),
            m4 := ItemSetVal()
        )

        root.set_value(0)
        root.for_all_except_self.set_value(10)
        root.for_sub.set_value(20)
        
        self.assertEqual(m1.get_value(), 10)
        self.assertEqual(root.for_all.get_value(), [0, 10, 20, 20])
        self.assertEqual(root.for_all_except_self.get_value(), [10, 20, 20])
        self.assertEqual(root.for_sub.get_value(), [20, 20])
        self.assertEqual(root.for_sub_p.get_value(), [(m3, 20), (m4, 20)])
        self.assertEqual(g1.for_all.get_value(), [10])

if __name__ == '__main__':
    unittest.main()
