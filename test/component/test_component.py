import unittest

from janim.components.component import Component, CmptInfo, CmptGroup
from janim.items.item import Item


class ComponentTest(unittest.TestCase):
    def test_component_group(self) -> None:
        called_list = []

        class MyCmpt(Component):
            def fn(self):
                called_list.append(self.fn)

            a = 1

        class MyItem(Item):
            cmpt1 = CmptInfo(MyCmpt)
            cmpt2 = CmptInfo(MyCmpt)
            cmpt = CmptGroup(cmpt1, cmpt2)

        item = MyItem()
        item.cmpt1.fn()
        item.cmpt.fn()

        self.assertListEqual(called_list, [item.cmpt1.fn, item.cmpt1.fn, item.cmpt2.fn])

        with self.assertRaises(AttributeError):
            item.cmpt.fn_not_exists

        with self.assertRaises(AttributeError):
            item.cmpt.a

    def test_component_group_err(self) -> None:
        class MyCmpt(Component): ...

        class MyItem(Item):
            cmpt1 = CmptInfo(MyCmpt)

        with self.assertRaises(ValueError):
            class MyItem2(MyItem):
                cmpt2 = CmptInfo(MyCmpt)
                cmpt = CmptGroup(MyItem.cmpt1, cmpt2)

            MyItem2()
