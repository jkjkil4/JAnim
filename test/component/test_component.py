import unittest

from janim.components.component import Component, CmptInfo, CmptGroup
from janim.items.item import Item, Group


class ComponentTest(unittest.TestCase):
    def test_component_group(self) -> None:
        called_list = []

        class MyCmpt(Component):
            def fn(self):
                called_list.append(self.fn)

            @property
            def property_without_as_able(self):
                pass

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

        with self.assertRaises(AttributeError):
            group.astype(MyItem).cmpt1.fn

        with self.assertRaises(AttributeError):
            group.astype(MyItem).cmpt1.fn_that_not_exists

        with self.assertRaises(AttributeError):
            group.astype(MyItem).cmpt1.a

        with self.assertRaises(AttributeError):
            group.astype(MyItem).cmpt1.property_without_as_able

    def test_component_group_err(self) -> None:
        class MyCmpt(Component): ...

        class MyItem(Item):
            cmpt1 = CmptInfo(MyCmpt)

        with self.assertRaises(ValueError):
            class MyItem2(MyItem):
                cmpt2 = CmptInfo(MyCmpt)
                cmpt = CmptGroup(MyItem.cmpt1, cmpt2)

            MyItem2()
