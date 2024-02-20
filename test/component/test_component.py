import unittest

from janim.components.component import Component, CmptInfo, CmptGroup
from janim.items.item import Item, Group


class ComponentTest(unittest.TestCase):
    def test_component_group(self) -> None:
        called_list = []

        class MyCmpt(Component, impl=True):
            def fn(self):
                called_list.append(self.fn)

            a = 1

        class MyItem(Item):
            cmpt1 = CmptInfo(MyCmpt)
            cmpt2 = CmptInfo(MyCmpt)
            cmpt = CmptGroup(cmpt1, cmpt2)
            b = 1

        item = MyItem()
        item.cmpt1.fn()
        item.cmpt.fn()

        self.assertListEqual(called_list, [item.cmpt1.fn, item.cmpt1.fn, item.cmpt2.fn])

        with self.assertRaises(AttributeError):
            item.cmpt.fn_not_exists

        with self.assertRaises(AttributeError):
            item.cmpt.a

        group = Group(item)

        with self.assertRaises(TypeError):
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

        with self.assertRaises(ValueError):
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
        self.assertIs(
            item2.cmpt.get_same_cmpt(item1),
            item1._astype_mock_cmpt[(MyItem, 'cmpt')]
        )

        self.assertIs(
            item2.astype(MyItem).cmpt,
            item2.cmpt
        )

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
