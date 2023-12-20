from janim.typing import Self

import unittest

from janim.items.item import Item, Group

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
                self.cnt = 0    # 用于记录 get_data 真正被调用的次数
                self.data = 0

            @Item.register_refresh_required
            def get_data(self) -> None:
                self.cnt += 1
                return self.data
        
        item = MyItem()
        
        # 一开始没调用 get_data，因此显然调用次数为 0
        self.assertEqual(item.cnt, 0)

        # 在这十次中，只有第一次是有真正执行 get_data 的，因此执行后调用次数为 1
        for i in range(10):
            item.get_data()
        self.assertEqual(item.cnt, 1)

        # 这里设置了 data 为 10，但是由于没有 mark_refresh_required，因此 get_data 的数据并没有被更新，所以应当为 0
        item.data = 10
        self.assertEqual(item.get_data(), 0)

        # 这里标记 mark_refresh_required，所以 get_data 可以得到更新，并且调用次数变为 2
        item.mark_refresh_required(MyItem.get_data)
        self.assertEqual(item.get_data(), 10)
        self.assertEqual(item.cnt, 2)

        # 之后这十次调用都没有真正调用 get_data，所以最终调用次数仍然为 2
        for i in range(10):
            item.get_data()
        self.assertEqual(item.cnt, 2)

    def test_group_method(self) -> None:
        class ItemA(Item):
            def __init__(self):
                super().__init__()
                self.val = 0

            def set_value(self, val):
                self.val = val
        
        class ItemB(Item): ...

        root = Group(
            g1 := Group(
                m1 := ItemA(),
                m2 := ItemB()
            ),
            m3 := ItemA()
        )
        
        root.set_value(10)

        self.assertEqual(root.get_family(), [root, g1, m1, m2, m3])
        self.assertEqual(m1.val, 10)
        self.assertEqual(m3.val, 10)
        

if __name__ == '__main__':
    unittest.main()
