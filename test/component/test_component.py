import unittest
from typing import Self

from janim.components.component import CmptGroup, CmptInfo, Component
from janim.exception import AsTypeError, CmptGroupLookupError
from janim.items.item import Item
from janim.items.points import Group


class ComponentTest(unittest.TestCase):
    def test_component(self) -> None:
        with self.assertRaises(AttributeError):
            class MyCmpt(Component):
                pass

        class MyCmpt1[T](Component[T], impl=True): ...
        class MyCmpt2[T](Component[T], impl=True): ...

        class MyItem(Item):
            cmpt1 = CmptInfo(MyCmpt1[Self])
            cmpt2 = CmptInfo(MyCmpt2[Self])

        item = MyItem()

        self.assertIs(item, item.cmpt1.r)
        self.assertIs(item.cmpt2, item.cmpt1.r.cmpt2)

    def test_component_group(self) -> None:
        called_list = []

        class MyCmpt(Component):
            def __init__(self):
                self.a = 1

            def copy(self) -> Self:
                return super().copy()

            def become(self, other) -> Self:
                self.a = other.a
                return self

            def not_changed(self, other) -> bool:
                return self.a == other.a

            def fn(self):
                called_list.append(self.fn)

        class MyItem(Item):
            cmpt1 = CmptInfo(MyCmpt)
            cmpt2 = CmptInfo(MyCmpt)
            cmpt = CmptGroup(cmpt1, cmpt2)
            b = 1

        item = MyItem()
        item.cmpt1.fn()
        item.cmpt.fn()

        self.assertListEqual(called_list, [item.cmpt1.fn, item.cmpt1.fn, item.cmpt2.fn])

        item_copy = item.copy()
        self.assertEqual(item_copy.cmpt1.a, item.cmpt1.a)
        self.assertEqual(item_copy.cmpt2.a, item.cmpt2.a)
        self.assertTrue(item_copy.cmpt.not_changed(item.cmpt))
        item_copy.cmpt2.a = 11
        self.assertNotEqual(item_copy.cmpt2.a, item.cmpt2.a)
        self.assertFalse(item_copy.cmpt.not_changed(item.cmpt))

        with self.assertRaises(AttributeError):
            item.cmpt.fn_not_exists

        with self.assertRaises(AttributeError):
            item.cmpt.a

        group = Group(item)

        with self.assertRaises(AsTypeError):
            group.astype(int)

        with self.assertRaises(AttributeError):
            group.astype(MyItem).b

        with self.assertRaises(AttributeError):
            group.astype(MyItem).cmpt_that_not_exists

    def test_component_group_err(self) -> None:
        class MyCmpt(Component, impl=True):
            pass

        class MyItem(Item):
            cmpt1 = CmptInfo(MyCmpt)

        with self.assertRaises(CmptGroupLookupError):
            class MyItem2(MyItem):
                cmpt2 = CmptInfo(MyCmpt)
                cmpt = CmptGroup(MyItem.cmpt1, cmpt2)

            MyItem2()

    def test_get_same_cmpt(self) -> None:
        class MyCmpt(Component, impl=True):
            pass

        class MyItem(Item):
            cmpt = CmptInfo(MyCmpt)

        item1 = Item()
        item2 = MyItem()
        item3 = MyItem()

        self.assertIs(
            item2.cmpt.get_same_cmpt(item2),
            item2.cmpt
        )
        self.assertIs(
            item2.cmpt.get_same_cmpt(item3),
            item3.cmpt
        )
        # self.assertIs(
        #     item2.cmpt.get_same_cmpt(item1),
        #     item1._astype_mock_cmpt['cmpt']
        # )

        # self.assertIs(
        #     item2.astype(MyItem).cmpt,
        #     item2.cmpt
        # )

    def test_inherit(self) -> None:
        class MyCmpt1(Component, impl=True):
            def fn1(self): ...

        class MyCmpt2(MyCmpt1, impl=True):
            def fn2(self): ...

        class MyCmpt3(Component, impl=True):
            def fn3(self): ...

        class MyItem1(Item):
            cmpt = CmptInfo(MyCmpt1)

        class MyItem2(MyItem1):
            cmpt = CmptInfo(MyCmpt2)

        class MyItem3(MyItem1):
            cmpt = CmptInfo(MyCmpt3)

        item1 = MyItem1()
        item1.cmpt.fn1()

        item2 = MyItem2()
        item2.cmpt.fn1()
        item2.cmpt.fn2()

        item3 = MyItem3()
        item3.cmpt.fn3()

        with self.assertRaises(AttributeError):
            item3.cmpt.fn1
