import unittest

from janim.items.item import Item
from janim.items.points import Group


class RelationTest(unittest.TestCase):
    def test_relation(self) -> None:
        root = Group(
            m1 := Item(),
            m2 := Item(),
            m3 := Group(
                m4 := Item(),
                m5 := Group(
                    m6 := Item(),
                    m7 := Item()
                ),
                m8 := Item()
            ),
            m9 := Item()
        )

        self.assertListEqual(m6.ancestors(), [m5, m3, root])
        self.assertListEqual(m5.descendants(), [m6, m7])
        self.assertListEqual(m3.descendants(), [m4, m5, m6, m7, m8])
        self.assertListEqual(root.descendants(), [m1, m2, m3, m4, m5, m6, m7, m8, m9])

        m2.add(
            m10 := Group(
                m11 := Item()
            )
        )
        m4.add(
            m12 := Item()
        )

        self.assertListEqual(root.descendants(), [m1, m2, m10, m11, m3, m4, m12, m5, m6, m7, m8, m9])

        m2.clear_children()
        m2.remove(m10)  # no effect
        self.assertListEqual(root.descendants(), [m1, m2, m3, m4, m12, m5, m6, m7, m8, m9])

        m4.clear_children()
        self.assertListEqual(root.descendants(), [m1, m2, m3, m4, m5, m6, m7, m8, m9])

        self.assertListEqual(list(root.walk_descendants()), [m1, m2, m3, m4, m5, m6, m7, m8, m9])

        m3.clear_parents()
        self.assertListEqual(root.descendants(), [m1, m2, m9])

    def test_relation_family(self) -> None:
        R = Item
        class C1(R): ...
        class C2(R): ...
        r'''
        m0(C1)
        | \____
        |      \
        m1(C1) m2(R)
        |  ____/\_________
        | /        \      \
        m3(C2)     m4(C2) m5(C1)
        |         _/______/
        |        /
        m6(R)   m7(C2)
        |  ____/
        | /
        m8(R)
        '''

        m: list[Item] = [C1(), C1(), R(), C2(), C2(), C1(), R(), C2(), R()]

        m[0].add(m[1], m[2])
        m[1].add(m[3])
        m[2].add(m[3], m[4], m[5])
        m[3].add(m[6])
        m[4].add(m[7])
        m[5].add(m[7])
        m[6].add(m[8])
        m[7].add(m[8])

        self.assertListEqual(list(m[8].walk_ancestors(C2)), [m[3], m[7], m[4]])
        self.assertListEqual(list(m[2].walk_self_and_ancestors()), [m[2], m[0]])
        self.assertListEqual(list(m[2].walk_self_and_descendants()), [m[2], m[3], m[6], m[8], m[4], m[7], m[5]])

        check_ancestors: list[tuple[int, list[int]]] = [
            (3, [1, 0, 2]),
            (8, [6, 3, 1, 0, 2, 7, 4, 5]),
            (7, [4, 2, 0, 5])
        ]
        check_descendants: list[tuple[int, list[int]]] = [
            (2, [3, 6, 8, 4, 7, 5]),
            (3, [6, 8])
        ]

        check_nearest_ancestors: list[tuple[int, type, list[int]]] = [
            (3, R, [1, 2]),
            (3, C1, [1]),
            (8, C2, [3, 7])
        ]

        check_nearest_descendants: list[tuple[int, type, list[int]]] = [
            (0, C2, [3, 4])
        ]

        for root, check in check_ancestors:
            self.assertListEqual(m[root].ancestors(), [m[idx] for idx in check])

        for root, check in check_descendants:
            self.assertListEqual(m[root].descendants(), [m[idx] for idx in check])

        for root, cls, check in check_nearest_ancestors:
            self.assertListEqual(list(m[root].walk_nearest_ancestors(cls)), [m[idx] for idx in check])

        for root, cls, check in check_nearest_descendants:
            self.assertListEqual(list(m[root].walk_nearest_descendants(cls)), [m[idx] for idx in check])
