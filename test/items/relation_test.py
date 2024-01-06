import unittest

from janim.items.relation import Relation
from janim.items.item import Group


class RelationTest(unittest.TestCase):
    def test_relation(self) -> None:
        root = Group(
            m1 := Relation(),
            m2 := Relation(),
            m3 := Group(
                m4 := Relation(),
                m5 := Group(
                    m6 := Relation(),
                    m7 := Relation()
                ),
                m8 := Relation()
            ),
            m9 := Relation()
        )

        self.assertEqual(m6.ancestors(), [m5, m3, root])
        self.assertEqual(m5.descendants(), [m6, m7])
        self.assertEqual(m3.descendants(), [m4, m5, m6, m7, m8])
        self.assertEqual(root.descendants(), [m1, m2, m3, m4, m5, m6, m7, m8, m9])

        m2.add(
            m10 := Group(
                m11 := Relation()
            )
        )
        m4.add(
            m12 := Relation()
        )

        self.assertEqual(root.descendants(), [m1, m2, m10, m11, m3, m4, m12, m5, m6, m7, m8, m9])

    def test_relation_family(self) -> None:
        '''
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
        R = Relation
        class C1(R): ...
        class C2(R): ...

        m: list[R] = [C1(), C1(), R(), C2(), C2(), C1(), R(), C2(), R()]

        m[0].add(m[1], m[2])
        m[1].add(m[3])
        m[2].add(m[3], m[4], m[5])
        m[3].add(m[6])
        m[4].add(m[7])
        m[5].add(m[7])
        m[6].add(m[8])
        m[7].add(m[8])

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

        for root, check in check_ancestors:
            self.assertEqual(m[root].ancestors(), [m[idx] for idx in check])

        for root, check in check_descendants:
            self.assertEqual(m[root].descendants(), [m[idx] for idx in check])

        for root, cls, check in check_nearest_ancestors:
            self.assertEqual(list(m[root].walk_nearest_ancestors(cls)), [m[idx] for idx in check])

if __name__ == '__main__':
    unittest.main()
