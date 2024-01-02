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

if __name__ == '__main__':
    unittest.main()
